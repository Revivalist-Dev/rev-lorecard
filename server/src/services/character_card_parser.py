import asyncio
import base64
import io
import json
import httpx
import yaml
from PIL import Image
import aichar
from typing import Dict, Any
from urllib.parse import urlparse, quote, unquote
from urllib.request import url2pathname
import re
from pathlib import Path

from logging_config import get_logger

logger = get_logger(__name__)

class CharacterCardParseError(Exception):
    """Custom exception for character card parsing failures."""
    pass


def _translate_windows_path_to_linux(path_str: str) -> str:
    """
    Translates a Windows drive path (e.g., D:\path\to\file) to a common
    Linux Docker mount path (e.g., /d/path/to/file).
    This assumes Docker Desktop is mounting drives as /c, /d, etc.
    """
    # Regex to match a single drive letter followed by a colon and a backslash
    # e.g., C:\ or D:\
    import re
    match = re.match(r'^([a-zA-Z]):[\\/](.*)', path_str)
    
    if match:
        drive_letter = match.group(1).lower()
        # Replace backslashes with forward slashes. We rely on Path() to handle special characters
        # like spaces and brackets, as they are valid in Linux filenames and should not be URL-quoted
        # when accessing the local filesystem via Docker volume mounts.
        rest_of_path = match.group(2).replace('\\', '/')
        # Construct the Linux path: /drive_letter/rest/of/path
        return f"/{drive_letter}/{rest_of_path}"
    
    return path_str

async def fetch_and_parse_character_card(url: str) -> str:
    """
    Fetches a character card from a URL (remote or local file path) and extracts
    the character data into a formatted string.
    """
    parsed_url = urlparse(url)
    content_bytes: bytes

    is_local_path = parsed_url.scheme in ('file', '') or (
        len(parsed_url.scheme) == 1 and parsed_url.scheme.isalpha()
    )

    if is_local_path:
        # Handle local file path, converting file:// URLs to system paths
        path_to_open = url
        if parsed_url.scheme == 'file':
            # Use url2pathname to handle Windows drive letters and path separators
            path_to_open = url2pathname(parsed_url.path)
            # Remove leading slash if present on Windows drive letter paths (e.g., /C:/...)
            if Path(path_to_open).drive and path_to_open.startswith('/'):
                path_to_open = path_to_open[1:]
        elif parsed_url.scheme and parsed_url.scheme.isalpha() and len(parsed_url.scheme) == 1:
            # Handle Windows drive letter paths like C:\... where 'C' is parsed as scheme
            path_to_open = url
        else:
            # Default to parsed_url.path for paths without scheme
            path_to_open = parsed_url.path

        # Attempt to translate Windows drive paths (e.g., D:\...) to Linux mount points (/d/...)
        translated_path = _translate_windows_path_to_linux(path_to_open)
        
        file_path = Path(translated_path)
        
        if not file_path.is_file():
            # Log the path we actually attempted to open (without resolving, which causes the Docker CWD issue)
            logger.error(f"Attempted to open path: {file_path}")
            raise CharacterCardParseError(f"Local file not found: {url}")
        
        try:
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
        except Exception as e:
            raise CharacterCardParseError(f"Failed to read local file {url}: {e}")
    elif parsed_url.scheme in ('http', 'https'):
        # Handle remote URL
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                content_bytes = response.content
        except httpx.HTTPStatusError as e:
            raise CharacterCardParseError(f"Failed to fetch remote URL {url}: HTTP error {e.response.status_code}")
        except httpx.RequestError as e:
            raise CharacterCardParseError(f"Failed to fetch remote URL {url}: Request error {e}")
    else:
        raise CharacterCardParseError(f"Unsupported URL scheme: {parsed_url.scheme}")

    # Determine if content is JSON/TXT, YAML, or PNG
    if url.lower().endswith(('.json', '.txt', '.yaml', '.yml')) or content_bytes.startswith(b'{'):
        content_str = content_bytes.decode('utf-8')
        
        # Determine if content is JSON or YAML based on extension or content start
        is_yaml = url.lower().endswith(('.yaml', '.yml')) or (not content_str.startswith('{') and not content_str.startswith('['))
        
        try:
            if is_yaml:
                # Use aichar for YAML parsing
                char_class = await asyncio.to_thread(aichar.load_character_yaml, content_str)
            else:
                # Use aichar for JSON parsing
                char_class = await asyncio.to_thread(aichar.load_character_json, content_str)
            
            # Convert CharacterClass object to a dictionary matching our expected structure
            data = {
                "name": char_class.name,
                "description": char_class.summary,
                "personality": char_class.personality,
                "scenario": char_class.scenario,
                "first_mes": char_class.greeting_message,
                "mes_example": char_class.example_messages,
            }
            
            # We skip _parse_json_card since aichar already handles V1/Pygmalion normalization
            
        except Exception as e:
            # If parsing fails, raise a clear error.
            logger.error(f"Failed to parse JSON/YAML card using aichar: {e}", exc_info=True)
            raise CharacterCardParseError(f"Failed to parse character card (JSON/YAML format). Underlying error: {e}")
    elif url.lower().endswith('.png') or content_bytes.startswith(b'\x89PNG'):
        # Use aichar for robust PNG parsing
        try:
            # aichar.load_character_card is synchronous, run it in a thread
            char_class = await asyncio.to_thread(aichar.load_character_card, content_bytes)
            
            # Convert CharacterClass object to a dictionary matching our expected structure
            data = {
                "name": char_class.name,
                "description": char_class.summary,
                "personality": char_class.personality,
                "scenario": char_class.scenario,
                "first_mes": char_class.greeting_message,
                "mes_example": char_class.example_messages,
            }
            
        except Exception as e:
            # If aichar fails, we raise a clear error.
            logger.error(f"Failed to parse PNG card using aichar: {e}", exc_info=True)
            raise CharacterCardParseError(f"Failed to parse character card (PNG format). Underlying error: {e}")
    else:
        raise CharacterCardParseError("Unsupported file format (must be JSON, TXT, YAML, or PNG).")

    # Format the extracted character data for LLM context
    # The data variable now holds the normalized dictionary from aichar parsing (PNG, JSON, or YAML)
    char_data = data

    formatted_content = f"CHARACTER CARD SOURCE: {url}\n\n"
    
    # Map common fields to a readable format
    fields_to_include = {
        "name": "Name",
        "description": "Description",
        "personality": "Personality",
        "persona": "Personality", # Handle alternative key
        "scenario": "Scenario",
        "first_mes": "First Message",
        "first_message": "First Message", # Handle alternative key
        "mes_example": "Example Messages",
        "example_messages": "Example Messages", # Handle alternative key
    }

    for key, label in fields_to_include.items():
        value = char_data.get(key)
        if value and isinstance(value, str):
            formatted_content += f"--- {label.upper()} ---\n{value.strip()}\n\n"

    return formatted_content.strip()
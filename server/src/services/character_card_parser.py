import base64
import io
import json
import httpx
from PIL import Image
from typing import Dict, Any
from urllib.parse import urlparse
from urllib.request import url2pathname
from pathlib import Path

from logging_config import get_logger

logger = get_logger(__name__)

class CharacterCardParseError(Exception):
    """Custom exception for character card parsing failures."""
    pass

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

        file_path = Path(path_to_open)
        
        if not file_path.is_file():
            logger.error(f"Attempted to open path: {file_path.resolve()}")
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

    # Determine if content is JSON or PNG
    if url.lower().endswith(('.json', '.txt')) or content_bytes.startswith(b'{'):
        # Assume JSON or raw text
        try:
            data = json.loads(content_bytes.decode('utf-8'))
        except json.JSONDecodeError:
            # If it's not JSON, treat it as raw text content
            return content_bytes.decode('utf-8').strip()
    elif url.lower().endswith('.png') or content_bytes.startswith(b'\x89PNG'):
        # Assume PNG card (SillyTavern v2 format)
        try:
            image = Image.open(io.BytesIO(content_bytes))
            metadata = image.info
            logger.debug(f"PNG metadata keys found: {list(metadata.keys())}")
            
            if 'ccv3' in metadata:
                # SillyTavern v3 format (takes precedence)
                encoded_data = metadata['ccv3']
                json_data = base64.b64decode(encoded_data).decode('utf-8')
                data = json.loads(json_data)
            elif 'chara' in metadata:
                # SillyTavern v2 format
                encoded_data = metadata['chara']
                json_data = base64.b64decode(encoded_data).decode('utf-8')
                data = json.loads(json_data)
            elif 'troll' in metadata:
                # Legacy/Troll format
                encoded_data = metadata['troll']
                json_data = base64.b64decode(encoded_data).decode('utf-8')
                data = json.loads(json_data)
            else:
                # Fallback: Extract all metadata as plain text
                logger.warning("PNG file does not contain 'chara' metadata. Extracting all metadata as plain text.")
                
                fallback_content = f"CHARACTER CARD SOURCE: {url} (Unsupported PNG format)\n\n"
                for key, value in metadata.items():
                    if isinstance(value, str) and len(value) < 1000: # Limit size for sanity
                        fallback_content += f"--- METADATA: {key.upper()} ---\n{value.strip()}\n\n"
                
                # Always return the fallback content if we reached this point, even if minimal.
                # This ensures the source is marked as fetched and the user can view the metadata.
                return fallback_content.strip()
        except Exception as e:
            raise CharacterCardParseError(f"Failed to parse PNG card: {e}")
    else:
        raise CharacterCardParseError("Unsupported file format (must be JSON, TXT, or PNG).")

    # Format the extracted character data for LLM context
    if 'spec' in data and data['spec'] == 'chara_card_v2':
        char_data = data['data']
    else:
        # Assume legacy or raw character data structure
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
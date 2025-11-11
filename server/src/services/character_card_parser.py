import json
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, quote, unquote
from urllib.request import url2pathname
from services.templates import render_template
import re
from pathlib import Path
from schemas import ContentType, CharacterCardClass
from services.templates import render_template

from logging_config import get_logger

logger = get_logger(__name__)

from exceptions import CharacterCardParseError
from services.character_card_processor import load_character_card_from_content, CharacterCardProcessorError

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

async def fetch_and_parse_character_card(url: str, output_format: ContentType) -> str:
    """
    Fetches a character card from a URL (remote or local file path) and extracts
    the character data into a formatted string based on the requested output_format.
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

    # Use the new synchronous processor directly, as file reading (local or remote) is already awaited.
    # We rely on the processor to detect the format (PNG, JSON, or YAML) from the bytes.
    try:
        # load_character_card_from_content handles both bytes (PNG) and string (JSON/YAML)
        char_class, raw_data = load_character_card_from_content(content_bytes)
        
        # Convert CharacterCardClass object to a dictionary for template rendering (normalized data)
        # We use model_dump() to get a dictionary representation, including V2/V3 fields.
        normalized_data = char_class.model_dump(by_alias=False, exclude_none=True)
        
    except CharacterCardProcessorError as e:
        logger.error(f"Failed to parse character card: {e}", exc_info=True)
        raise CharacterCardParseError(f"Failed to parse character card. Underlying error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during character card parsing: {e}", exc_info=True)
        raise CharacterCardParseError(f"Unexpected error during character card parsing. Underlying error: {e}")

    # The normalized_data variable holds the canonical representation for Markdown output.
    # The raw_data variable holds the dictionary extracted directly from the file for JSON output.

    if output_format.value == ContentType.JSON.value:
        # For JSON output, return the raw data dictionary directly, as requested by the user.
        # We check for V2/V3 structure and extract the nested 'data' object if present,
        # as this is what card_extractor.py did to match user expectation.
        data_to_output = raw_data
        if data_to_output.get('spec', '').startswith('chara_card_v'):
            data_to_output = data_to_output.get('data', data_to_output)
            
        # Return raw JSON string directly, bypassing Jinja rendering for simplicity and purity.
        return json.dumps(data_to_output, indent=2, ensure_ascii=False)
    
    # --- Markdown Output Path ---
    
    # Ensure all values are strings or objects, replacing None with appropriate defaults for template rendering.
    # This prevents core fields from being dropped from the template context and avoids errors with filters like 'join'.
    list_fields = ['alternate_greetings', 'tags']
    dict_fields = ['extensions', 'character_book']
    
    filtered_data = {}
    for k, v in normalized_data.items():
        if v is None:
            if k in list_fields:
                filtered_data[k] = []
            elif k in dict_fields:
                filtered_data[k] = {}
            else:
                filtered_data[k] = ""
        else:
            filtered_data[k] = v
    
    context = {
        "url": url,
        "char_data": filtered_data,
    }
    template_path = "services/parsers/character_card_markdown.jinja2"

    try:
        # Render the template
        return render_template(template_path, context)
    except Exception as e:
        logger.error(f"Failed to render character card template {template_path}: {e}", exc_info=True)
        # Fallback to a simple string representation if template rendering fails
        format_str = getattr(output_format, 'value', str(output_format))
        return f"Error rendering card in {format_str} format: {e}\n\nRaw Data:\n{json.dumps(normalized_data, indent=2)}"
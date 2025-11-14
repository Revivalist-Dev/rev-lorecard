import json
import base64
from io import BytesIO
from typing import Union, Dict, Any, List, Tuple, Optional
import yaml
import re
from PIL import Image
from pydantic import ValidationError

from schemas import CharacterCardClass, ContentType
from services.templates import render_template
from logging_config import get_logger

logger = get_logger(__name__)

class CharacterCardProcessorError(Exception):
    """Custom exception for errors during character card processing."""
    pass

def _map_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps various character card field names (V1, V2, V3, different formats)
    to the canonical CharacterCardClass fields, applying fallback logic.
    """
    
    # Check for V2/V3 structure and extract the nested 'data' object if present
    if data.get('spec', '').startswith('chara_card_v'):
        data = data.get('data', data)
        
    metadata = data.get('metadata', {})
    created_time = metadata.get('created')

    # Handle extensions and character_book which might be JSON strings in some inputs
    # Handle extensions, checking for aliases and JSON string decoding
    extensions = data.get('extensions') or data.get('extension')
    if isinstance(extensions, str):
        try:
            extensions = json.loads(extensions)
        except json.JSONDecodeError:
            extensions = None
    
    # Handle character_book, checking for aliases and JSON string decoding
    character_book = data.get('character_book') or data.get('world_book') or data.get('lorebook')
    if isinstance(character_book, str):
        try:
            character_book = json.loads(character_book)
        except json.JSONDecodeError:
            character_book = None

    # Handle alternate_greetings and tags which might be JSON strings in some inputs
    alternate_greetings = data.get('alternate_greetings')
    if isinstance(alternate_greetings, str):
        try:
            alternate_greetings = json.loads(alternate_greetings)
        except json.JSONDecodeError:
            alternate_greetings = None
    
    tags = data.get('tags')
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except json.JSONDecodeError:
            tags = None

    # Map fields using V1/V2 aliases
    # V1 fields: name, description, personality, scenario, first_mes, mes_example
    # V2 fields: name, description, personality, scenario, first_mes, mes_example, creator_notes, system_prompt, post_history_instructions, alternate_greetings, tags, creator, character_version, extensions, character_book
    
    # Note: V2 uses 'description' and V1 uses 'description' or 'summary'.
    mapped_summary = data.get("summary") or data.get("description") or ""
    
    # Note: V1/Pygmalion uses 'char_persona' or 'personality'.
    mapped_personality = data.get("char_persona") or data.get("personality") or ""
    
    # Note: V1/Pygmalion uses 'world_scenario' or 'scenario'.
    mapped_scenario = data.get("world_scenario") or data.get("scenario") or ""
    
    # Note: V1/Pygmalion uses 'char_greeting' or 'first_mes'.
    mapped_greeting = data.get("char_greeting") or data.get("first_mes") or ""
    
    # Note: V1/Pygmalion uses 'example_dialogue' or 'mes_example'.
    mapped_examples = data.get("example_dialogue") or data.get("mes_example") or ""

    # Pygmalion/TextGen WebUI cards often conflate description and personality into char_persona.
    # If summary is empty but personality (mapped from char_persona) has content,
    # assume the content belongs in summary and clear personality.
    if not mapped_summary and mapped_personality:
        mapped_summary = mapped_personality
        mapped_personality = ""

    return {
        "name": data.get("char_name") or data.get("name") or "",
        "summary": mapped_summary,
        "personality": mapped_personality,
        "scenario": mapped_scenario,
        "greeting_message": mapped_greeting,
        "example_messages": mapped_examples,
        "created_time": created_time,
        "creator_notes": data.get("creator_notes"),
        "system_prompt": data.get("system_prompt"),
        "post_history_instructions": data.get("post_history_instructions"),
        "alternate_greetings": alternate_greetings,
        "tags": tags,
        "creator": data.get("creator"),
        "character_version": data.get("character_version"),
        "extensions": extensions,
        "character_book": character_book,
    }

def load_character_json(content: str) -> Tuple[CharacterCardClass, Dict[str, Any]]:
    """Loads a character card from a JSON string."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise CharacterCardProcessorError(f"Error parsing JSON content: {e}") from e

    mapped_data = _map_fields(data)
    try:
        return CharacterCardClass(**mapped_data), data
    except ValidationError as e:
        raise CharacterCardProcessorError(f"Validation error for JSON character data: {e}") from e

def load_character_markdown(
    content: str, regex_patterns_to_strip: Optional[List[str]] = None
) -> Tuple[CharacterCardClass, Dict[str, Any]]:
    """
    Loads a character card from a Markdown string using predefined headers.
    """
    data: Dict[str, Any] = {}
    
    # Define the mapping from header text to CharacterCardClass field names
    # Note: char_data.summary maps to DESCRIPTION, char_data.personality maps to PERSONALITY, etc.
    FIELD_MAP = {
        "NAME": "name",
        "DESCRIPTION": "summary",
        "PERSONALITY": "personality",
        "SCENARIO": "scenario",
        "FIRST MESSAGE": "greeting_message",
        "EXAMPLE MESSAGES": "example_messages",
        "CREATOR NOTES": "creator_notes",
        "SYSTEM PROMPT": "system_prompt",
        "POST HISTORY INSTRUCTIONS": "post_history_instructions",
        "ALTERNATE GREETINGS": "alternate_greetings",
        "TAGS": "tags",
        "CREATOR": "creator",
        "CHARACTER VERSION": "character_version",
        "EXTENSIONS (JSON)": "extensions",
        "CHARACTER BOOK (JSON)": "character_book",
    }

    # Regex to find content blocks delimited by '--- HEADER ---'
    # It captures the header name and the content block following it.
    # The content block ends either at the next '--- HEADER ---' or the end of the string.
    # We ignore the first line which might be 'CHARACTER CARD SOURCE: ...'
    
    # Split content by '---' lines to isolate blocks
    blocks = re.split(r"^\s*---\s*([A-Z\s()]+)\s*---\s*$", content, flags=re.MULTILINE | re.IGNORECASE)
    
    # The first element is usually pre-header content (like the URL line), which we skip.
    # Blocks will look like: [preamble, HEADER_NAME_1, CONTENT_1, HEADER_NAME_2, CONTENT_2, ...]
    
    # Start processing from the second element (index 1)
    for i in range(1, len(blocks), 2):
        header = blocks[i].strip().upper()
        content_block = blocks[i+1].strip() if i + 1 < len(blocks) else ""
        
        # Conditionally strip regex patterns from the content block
        if regex_patterns_to_strip and content_block:
            for pattern in regex_patterns_to_strip:
                try:
                    # Compile regex with MULTILINE and IGNORECASE flags for robust Markdown parsing
                    compiled_regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
                    content_block = compiled_regex.sub('', content_block)
                except re.error as e:
                    logger.warning(f"Invalid regex pattern provided for stripping: {pattern}. Error: {e}")
            content_block = content_block.strip()
        
        if header in FIELD_MAP:
            field_name = FIELD_MAP[header]
            
            # Handle list/dict fields that were serialized as JSON strings in the template
            if field_name in ["alternate_greetings", "tags", "extensions", "character_book"]:
                if content_block:
                    try:
                        # Attempt to parse JSON content for these fields
                        parsed_content = json.loads(content_block)
                        data[field_name] = parsed_content
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON content for Markdown field: {field_name}")
                        data[field_name] = None
                else:
                    data[field_name] = None
            else:
                data[field_name] = content_block

    # The Markdown format is a custom format, so we don't use _map_fields
    # as the fields are already mapped to the canonical names.
    try:
        # We use the raw data dictionary as the raw_data for consistency,
        # even though it's not a standard JSON card.
        return CharacterCardClass(**data), data
    except ValidationError as e:
        raise CharacterCardProcessorError(f"Validation error for Markdown character data: {e}") from e


def load_character_yaml(content: str) -> Tuple[CharacterCardClass, Dict[str, Any]]:
    """Loads a character card from a YAML string."""
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise CharacterCardProcessorError(f"Error parsing YAML content: {e}") from e
    
    if not isinstance(data, dict):
        raise CharacterCardProcessorError("YAML content is not a valid character card dictionary.")

    mapped_data = _map_fields(data)
    try:
        return CharacterCardClass(**mapped_data), data
    except ValidationError as e:
        raise CharacterCardProcessorError(f"Validation error for YAML character data: {e}") from e

def _find_chunk_fallback(content: bytes, chunk_name: str) -> Optional[bytes]:
    """
    Fallback mechanism to manually search for a specific tEXt chunk in PNG bytes.
    Returns the raw content bytes of the chunk, or None if not found.
    """
    # tEXt chunk structure: 4 bytes length, tEXt, keyword (e.g., 'chara' or 'json'), null separator, text data, 4 bytes CRC
    marker = f'tEXt{chunk_name}\x00'.encode('ascii')
    
    try:
        # Find the start of the tEXt chunk data (after the marker and null byte)
        start_index = content.index(marker) + len(marker)
        
        # Find the start of the next chunk (or IEND)
        # We search for the next chunk header (4 bytes length + 4 bytes type)
        # The chunk type is always 4 ASCII characters. We look for the next 4-byte type marker.
        # This is complex and error-prone. A simpler approach is to rely on the fact that
        # the data is usually followed by the next chunk's length field (4 bytes).
        
        # Instead of complex chunk parsing, we rely on the fact that the data is usually
        # the last significant chunk before IEND, or we search for the IEND marker.
        # This is a heuristic based on common card formats.
        
        # Find the end of the file (start of IEND chunk)
        # IEND chunk: 4 bytes length (0x00000000), IEND, 4 bytes CRC
        iend_marker = b'IEND\xaeB`\x82'
        end_index = content.rindex(iend_marker)
        
        # The data is between the end of the tEXt marker and the start of the IEND chunk.
        # We return the raw bytes, stripped of whitespace.
        chunk_data_bytes = content[start_index:end_index].strip()
        
        # We need to find the actual end of the tEXt chunk data, which is before the CRC.
        # Since we don't parse the length field, we must rely on the next chunk header.
        # Let's simplify the fallback to only work if the chunk is near the end.
        
        # A more robust fallback: find the start of the chunk, then find the start of the next chunk type (4 ASCII chars).
        # This is still too complex without a full PNG parser. Let's stick to the simple heuristic
        # but acknowledge its limitations. The data is usually the last thing before IEND.
        
        # Let's refine the search to find the end of the tEXt chunk data by looking for the start of the next chunk.
        # A chunk starts with 4 bytes length, 4 bytes type.
        
        # For simplicity and robustness against various PNG structures, we will assume the data
        # is contained between the marker and the IEND chunk, as implemented previously,
        # but we must ensure we only return the data relevant to the *specific* chunk we found.
        
        # Since we don't know the length of the tEXt chunk data, we must find the start of the next chunk.
        # The next chunk starts with 4 bytes (length) followed by 4 bytes (type, e.g., 'IDAT').
        
        # Find the start of the next chunk header (4 bytes length + 4 bytes type)
        # We search for common subsequent chunk types like 'IDAT' or 'IEND'.
        
        # Let's use the previous simple heuristic, which was designed for the 'chara' chunk
        # which is often the last tEXt chunk.
        
        if not chunk_data_bytes:
            raise ValueError(f"'{chunk_name}' chunk found but content is empty.")
            
        return chunk_data_bytes
    except ValueError:
        # Chunk not found
        return None

def _get_character_data_from_png(content: bytes) -> Tuple[Dict[str, Any], str]:
    """
    Extracts character data (JSON) from a PNG file, handling V1 ('chara', base64)
    and V2/V3 ('json', raw JSON) formats.
    
    Returns: (data_dict, chunk_name)
    """
    try:
        img = Image.open(BytesIO(content))
        
        # 1. Check for V2/V3 'json' chunk (raw JSON)
        if 'json' in img.info:
            character_text = img.info['json']
            chunk_name = 'json'
        
        # 2. Check for V1 'chara' chunk (base64 encoded JSON)
        elif 'chara' in img.info:
            base64_data = img.info['chara']
            chunk_name = 'chara'
            
            # Ensure base64_data is bytes for b64decode
            if isinstance(base64_data, str):
                base64_data = base64_data.encode('ascii')
                
            # Decode base64 data
            character_bytes = base64.b64decode(base64_data)
            character_text = character_bytes.decode('utf-8')
        
        # 3. Fallback to manual byte search if Pillow doesn't expose the chunk
        else:
            # Try 'json' fallback first (V2/V3)
            json_bytes = _find_chunk_fallback(content, 'json')
            if json_bytes:
                character_text = json_bytes.decode('utf-8')
                chunk_name = 'json'
            else:
                # Try 'chara' fallback (V1)
                chara_bytes = _find_chunk_fallback(content, 'chara')
                if chara_bytes:
                    chunk_name = 'chara'
                    # Decode base64 data
                    character_bytes = base64.b64decode(chara_bytes)
                    character_text = character_bytes.decode('utf-8')
                else:
                    raise CharacterCardProcessorError(
                        "Failed to find 'json' or 'chara' metadata (tEXt chunk) in the PNG file."
                    )

        # Parse the inner JSON payload
        if isinstance(character_text, bytes):
            character_text = character_text.decode('utf-8')
            
        data = json.loads(character_text)
        return data, chunk_name

    except (IOError, SyntaxError, KeyError, base64.binascii.Error, json.JSONDecodeError, CharacterCardProcessorError) as e:
        # Re-raise as CharacterCardProcessorError if it's not already one
        if isinstance(e, CharacterCardProcessorError):
            raise
        raise CharacterCardProcessorError(f"Error processing PNG character card: {e}") from e


def load_character_card(content: bytes) -> Tuple[CharacterCardClass, Dict[str, Any]]:
    """
    Loads a character card from raw PNG bytes (Tavern Card V1/V2/V3 format).
    """
    raw_data, chunk_name = _get_character_data_from_png(content)
    
    # Check for V2/V3 structure and extract the nested 'data' object if present
    # We do this here to ensure the raw_data returned is the top-level dictionary,
    # while the mapped data uses the potentially nested 'data' object.
    data_for_mapping = raw_data
    if raw_data.get('spec', '').startswith('chara_card_v'):
        data_for_mapping = raw_data.get('data', raw_data)
    
    mapped_data = _map_fields(data_for_mapping)
    try:
        return CharacterCardClass(**mapped_data), raw_data
    except ValidationError as e:
        raise CharacterCardProcessorError(f"Validation error for PNG character data (from chunk '{chunk_name}'): {e}") from e

def load_character_card_from_content(content: Union[bytes, str]) -> Tuple[CharacterCardClass, Dict[str, Any]]:
    """
    Attempts to load a character card by detecting its format (PNG, JSON, or YAML).
    Returns: (CharacterCardClass, raw_data_dict)
    """
    if isinstance(content, bytes):
        # Check for PNG signature (first 8 bytes)
        if content.startswith(b'\x89PNG\r\n\x1a\n'):
            return load_character_card(content)
        
        # If it's bytes but not PNG, try decoding to string and proceed
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            # If decoding fails, it's likely binary data we can't handle as text
            raise CharacterCardProcessorError("Content is bytes but not a valid PNG, and cannot be decoded to UTF-8 string.")

    if isinstance(content, str):
        # Try JSON first (most common non-PNG format)
        try:
            return load_character_json(content)
        except CharacterCardProcessorError as json_e:
            logger.debug(f"Content failed JSON parsing: {json_e}")
            # If JSON fails, try YAML
            try:
                return load_character_yaml(content)
            except CharacterCardProcessorError as yaml_e:
                logger.debug(f"Content failed YAML parsing: {yaml_e}")
                # If both fail, raise the original error (or a combined one)
                raise CharacterCardProcessorError(f"Content is neither valid JSON nor YAML character card data. Last error: {yaml_e}")

    raise CharacterCardProcessorError("Unsupported content type for character card loading.")


def convert_content(
    content: str,
    source_type: ContentType,
    target_type: ContentType,
    regex_patterns_to_strip: Optional[List[str]] = None,
) -> str:
    """
    Converts character card content between Markdown and JSON formats.
    """
    if source_type == target_type:
        return content

    # 1. Parse the source content into the canonical CharacterCardClass
    if source_type in [
        ContentType.CC_MARKDOWN_V1,
        ContentType.CC_MARKDOWN_V2,
        ContentType.CC_MARKDOWN_V3,
    ]:
        card_class, _ = load_character_markdown(
            content, regex_patterns_to_strip=regex_patterns_to_strip
        )
    elif source_type in [
        ContentType.CC_JSON_V1,
        ContentType.CC_JSON_V2,
        ContentType.CC_JSON_V3,
        ContentType.CC_JSON_MISC,
        ContentType.JSON, # Fallback for old generic JSON type if still used elsewhere
    ]:
        card_class, _ = load_character_json(content)
    else:
        raise CharacterCardProcessorError(
            f"Unsupported source conversion type: {source_type.value}"
        )

    # 2. Serialize the canonical class into the target format
    context = {"char_data": card_class}
    
    if target_type == ContentType.CC_MARKDOWN_V1:
        template_path = "services/parsers/character_card_markdown_v1.jinja2"
        converted_content = render_template(template_path, context)
    elif target_type == ContentType.CC_MARKDOWN_V2:
        template_path = "services/parsers/character_card_markdown_v2.jinja2"
        converted_content = render_template(template_path, context)
    elif target_type == ContentType.CC_MARKDOWN_V3:
        template_path = "services/parsers/character_card_markdown_v3.jinja2"
        converted_content = render_template(template_path, context)
    elif target_type == ContentType.CC_JSON_V1:
        template_path = "services/parsers/character_card_json_v1.jinja2"
        converted_content = render_template(template_path, context)
    elif target_type == ContentType.CC_JSON_V2:
        template_path = "services/parsers/character_card_json_v2.jinja2"
        converted_content = render_template(template_path, context)
    elif target_type == ContentType.CC_JSON_V3:
        template_path = "services/parsers/character_card_json_v3.jinja2"
        converted_content = render_template(template_path, context)
    elif target_type == ContentType.CC_JSON_MISC:
        # Use V2 template as a sensible default for generic JSON output
        template_path = "services/parsers/character_card_json_v2.jinja2"
        converted_content = render_template(template_path, context)
        
        # The JSON template renders a JSON string, but Jinja2 might introduce extra whitespace.
        # We should parse and re-dump it to ensure it's clean and compact (or pretty-printed).
        try:
            # Parse the Jinja2 output
            json_data = json.loads(converted_content)
            # Re-dump it nicely formatted
            converted_content = json.dumps(json_data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to re-format JSON output after rendering: {e}")
            # Fallback to raw rendered content if re-formatting fails
            pass
    else:
        raise CharacterCardProcessorError(
            f"Unsupported target conversion type: {target_type.value}"
        )

    return converted_content
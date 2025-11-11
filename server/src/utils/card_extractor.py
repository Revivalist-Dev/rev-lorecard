import sys
import json
import base64
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Tuple
from PIL import Image

class CardExtractorError(Exception):
    """Custom exception for errors during card extraction."""
    pass

def _find_chunk_fallback(content: bytes, chunk_name: str) -> bytes | None:
    """
    Simplified fallback mechanism to manually search for a specific tEXt chunk in PNG bytes.
    Returns the raw content bytes of the chunk, or None if not found.
    (Copied from character_card_processor.py for standalone utility)
    """
    marker = f'tEXt{chunk_name}\x00'.encode('ascii')
    
    try:
        start_index = content.index(marker) + len(marker)
        iend_marker = b'IEND\xaeB`\x82'
        end_index = content.rindex(iend_marker)
        
        chunk_data_bytes = content[start_index:end_index].strip()
        
        if not chunk_data_bytes:
            return None
            
        return chunk_data_bytes
    except ValueError:
        return None

def extract_raw_data_from_card(file_path: str) -> Dict[str, Any]:
    """
    Extracts the raw JSON data dictionary from a character card file (PNG, JSON, or YAML).
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise CardExtractorError(f"File not found: {file_path}")

    content = file_path.read_bytes()

    # 1. Try PNG
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        try:
            img = Image.open(BytesIO(content))
            
            if 'json' in img.info:
                character_text = img.info['json']
            elif 'chara' in img.info:
                base64_data = img.info['chara']
                if isinstance(base64_data, str):
                    base64_data = base64_data.encode('ascii')
                character_bytes = base64.b64decode(base64_data)
                character_text = character_bytes.decode('utf-8')
            else:
                # Fallback to manual byte search
                json_bytes = _find_chunk_fallback(content, 'json')
                if json_bytes:
                    character_text = json_bytes.decode('utf-8')
                else:
                    chara_bytes = _find_chunk_fallback(content, 'chara')
                    if chara_bytes:
                        character_bytes = base64.b64decode(chara_bytes)
                        character_text = character_bytes.decode('utf-8')
                    else:
                        raise CardExtractorError("Failed to find 'json' or 'chara' metadata in PNG.")

            if isinstance(character_text, bytes):
                character_text = character_text.decode('utf-8')
                
            return json.loads(character_text)

        except Exception as e:
            raise CardExtractorError(f"Error processing PNG card: {e}") from e

    # 2. Try JSON/YAML (read as string)
    try:
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        raise CardExtractorError("File is not PNG and cannot be decoded as UTF-8 text.")

    # Try JSON
    try:
        return json.loads(content_str)
    except json.JSONDecodeError:
        pass

    # Try YAML
    try:
        data = yaml.safe_load(content_str)
        if isinstance(data, dict):
            return data
    except yaml.YAMLError:
        pass

    raise CardExtractorError("File is not a recognized character card format (PNG, JSON, or YAML).")


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m server.src.utils.card_extractor <path_to_character_card_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    
    try:
        raw_data = extract_raw_data_from_card(file_path)
        
        # Check for V2/V3 structure and extract the nested 'data' object if present
        if raw_data.get('spec', '').startswith('chara_card_v'):
            raw_data = raw_data.get('data', raw_data)
            
        print(json.dumps(raw_data, indent=2))
        
    except CardExtractorError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Need to import yaml for the utility script
    import yaml
    main()
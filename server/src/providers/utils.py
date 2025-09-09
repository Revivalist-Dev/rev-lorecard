import json
import re
from typing import Any, Dict, Optional


def generate_example_from_schema(schema: Dict[str, Any]) -> str:
    """Generates a simple, deterministic example JSON object from a schema."""
    example = {}
    properties = schema.get("properties", {})
    for key, prop in properties.items():
        prop_type = prop.get("type")
        if prop_type == "string":
            example[key] = f"string value for {key}"
        elif prop_type == "number" or prop_type == "integer":
            example[key] = 123
        elif prop_type == "boolean":
            example[key] = True
        elif prop_type == "array":
            example[key] = []
        elif prop_type == "object":
            example[key] = {}  # Keep nested examples simple
        else:
            example[key] = None
    return json.dumps(example, indent=2)


def extract_json_from_code_block(text: str) -> Optional[str]:
    """Finds and extracts the content of a JSON markdown code block."""
    match = re.search(r"```(?:\w+\n|\n)([\s\S]*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback for models that might just return raw JSON
    match = re.search(r"^{\s*.*}", text, re.DOTALL)
    if match:
        return match.group(0).strip()
    return None

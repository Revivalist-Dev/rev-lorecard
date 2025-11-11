import re
import json
from typing import Dict, Any, Literal
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from providers.index import ChatMessage
from logging_config import get_logger

logger = get_logger(__name__)

# Define the base directory for templates relative to the project root
# Path(__file__).parent is server/src/services
# Path(__file__).parent.parent is server/src
TEMPLATE_BASE_DIR = Path(__file__).parent.parent

env = Environment(
    loader=FileSystemLoader(TEMPLATE_BASE_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
)

env.filters["tojson"] = lambda value, indent=None: json.dumps(value, indent=indent)


def render_template(template_path: str, context: Dict[str, Any]) -> str:
    """Renders a template file and returns the resulting string content."""
    template = env.get_template(template_path)
    return template.render(context)




def render_prompt(template_str: str, context: Dict[str, Any]) -> str:
    """Renders a prompt from a template string and context."""
    template = env.from_string(template_str)
    return template.render(context)


def create_messages_from_template(
    template_str: str, context: dict
) -> list[ChatMessage]:
    """
    Creates a list of ChatMessage objects from a template string.
    This version uses a more robust delimiter "--- role: <role>" to avoid
    conflicts with markdown horizontal rules.
    """
    messages = []

    # The pattern now looks for "--- role: <rolename>" at the beginning of a line,
    # capturing the role and all content until the next such delimiter or the end of the string.
    pattern = re.compile(
        r"^---\s*role:\s*(\w+)\s*\n(.*?)(?=\n^---\s*role:|\Z)", re.S | re.M
    )
    matches = pattern.findall(template_str)

    if not matches:
        # If no delimiters are found, treat the whole template as a single user message.
        # This provides backward compatibility for simple, single-message prompts.
        if template_str.strip():
            messages.append(
                ChatMessage(
                    role="user", content=render_prompt(template_str.strip(), context)
                )
            )
        return messages

    for role_str, content_str in matches:
        role: Literal["system", "user", "assistant"] = "user"
        cleaned_role = role_str.strip().lower()

        if cleaned_role in ("system", "user", "assistant"):
            role = cleaned_role  # pyright: ignore[reportAssignmentType]

        content = content_str.strip()
        if content:
            messages.append(
                ChatMessage(role=role, content=render_prompt(content, context))
            )

    return messages

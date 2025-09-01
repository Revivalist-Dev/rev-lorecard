import re
from typing import Dict, Any, Literal
from jinja2 import Environment, FileSystemLoader
from providers.index import ChatMessage
from logging_config import get_logger

logger = get_logger(__name__)

env = Environment(
    loader=FileSystemLoader("."),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_prompt(template_str: str, context: Dict[str, Any]) -> str:
    """Renders a prompt from a template string and context."""
    template = env.from_string(template_str)
    return template.render(context)


def create_messages_from_template(
    template_str: str, context: dict
) -> list[ChatMessage]:
    """Creates a list of ChatMessage objects from a template string."""
    messages = []

    template_str = render_prompt(template_str, context)

    # Regex to find all frontmatter blocks and the content that follows them
    pattern = re.compile(r"^---\s*\n(.*?)\n^---\s*\n(.*?)(?=\n^---|\Z)", re.S | re.M)
    matches = pattern.findall(template_str)

    if not matches:
        # If no frontmatter is found, treat the whole template as a single user message
        if template_str.strip():
            content = render_prompt(template_str, context)
            messages.append(ChatMessage(role="user", content=content))
        return messages

    for frontmatter_str, content_str in matches:
        role: Literal["system", "user", "assistant"] = "user"  # Default role
        # simple regex to extract role
        role_match = re.search(r"role:\s*(\w+)", frontmatter_str)
        if role_match:
            role = role_match.group(1)  # pyright: ignore[reportAssignmentType]

        if content_str.strip():
            rendered_content = render_prompt(content_str.strip(), context)
            messages.append(ChatMessage(role=role, content=rendered_content))

    return messages

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
    """
    Creates a list of ChatMessage objects from a template string.
    This version uses a more robust delimiter "--- role: <role>" to avoid
    conflicts with markdown horizontal rules.
    """
    messages = []
    rendered_template = render_prompt(template_str, context)

    # The pattern now looks for "--- role: <rolename>" at the beginning of a line,
    # capturing the role and all content until the next such delimiter or the end of the string.
    pattern = re.compile(
        r"^---\s*role:\s*(\w+)\s*\n(.*?)(?=\n^---\s*role:|\Z)", re.S | re.M
    )
    matches = pattern.findall(rendered_template)

    if not matches:
        # If no delimiters are found, treat the whole template as a single user message.
        # This provides backward compatibility for simple, single-message prompts.
        if rendered_template.strip():
            messages.append(ChatMessage(role="user", content=rendered_template.strip()))
        return messages

    for role_str, content_str in matches:
        role: Literal["system", "user", "assistant"] = "user"
        cleaned_role = role_str.strip().lower()

        if cleaned_role in ("system", "user", "assistant"):
            role = cleaned_role  # pyright: ignore[reportAssignmentType]

        content = content_str.strip()
        if content:
            messages.append(ChatMessage(role=role, content=content))

    return messages

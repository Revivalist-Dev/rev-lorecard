from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from enum import Enum

class ContentType(str, Enum):
    """
    Defines the supported content types for sources and character card extraction.
    """

    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    PLAINTEXT = "plaintext"
    HTML = "html"

class SelectorResponse(BaseModel):
    """
    Represents the expected JSON structure for a selector generation response,
    distinguishing between content and category links.
    """

    content_selectors: List[str] = Field(
        ...,
        description="A list of CSS selectors that target links to final content pages (e.g., character profiles).",
    )
    category_selectors: List[str] = Field(
        default_factory=list,
        description="A list of CSS selectors for links that lead to other category/list pages.",
    )
    pagination_selector: Optional[str] = Field(
        None, description="A CSS selector for the 'next page' link, if any."
    )


class LorebookEntryData(BaseModel):
    """
    Represents the expected JSON structure for a lorebook entry.
    """

    title: str = Field(..., description="The main title of the lore entry.")
    content: str = Field(..., description="The summarized body of the lore entry.")
    keywords: List[str] = Field(
        ...,
        description="A list of keywords that can be used to trigger this entry in a roleplay application.",
    )


class LorebookEntryResponse(BaseModel):
    """
    Represents the full response from the LLM for entry creation, including validation.
    """

    valid: bool = Field(
        ..., description="Whether the content meets the provided criteria."
    )
    reason: Optional[str] = Field(
        None, description="The reason for skipping the entry if it's not valid."
    )
    entry: Optional[LorebookEntryData] = Field(
        None, description="The generated lorebook entry if the content is valid."
    )


class SearchParamsResponse(BaseModel):
    """
    Represents the expected JSON structure for a search params generation response.
    """

    purpose: str = Field(..., description="Clear statement based on request type.")
    extraction_notes: str = Field(..., description="Guidelines for extraction.")
    criteria: str = Field(..., description="Simple validation requirements.")


class CharacterCardData(BaseModel):
    """
    Represents the expected JSON structure for a full character card.
    """

    name: str = Field(..., description="The character's full name.")
    description: str = Field(
        ..., description="A detailed physical and general description of the character."
    )
    persona: str = Field(
        ...,
        description="A detailed description of the character's personality, demeanor, and inner thoughts.",
    )
    scenario: str = Field(
        ..., description="The setting or scenario the character is in."
    )
    first_message: str = Field(
        ...,
        description="The character's first message to the user, written in a roleplay style.",
    )
    example_messages: str = Field(
        ...,
        description="Several example dialogue exchanges, formatted with placeholders like {{user}} and {{char}}.",
    )


class RegeneratedFieldResponse(BaseModel):
    """
    Represents the expected JSON response when regenerating a single field.
    """

    new_content: str = Field(
        ..., description="The newly generated text for the requested field."
    )


class CharacterCardClass(BaseModel):
    """
    Represents the full data structure of a character card, including V1, V2, and V3 fields.
    This replaces the Rust CharacterClass object.
    """
    name: str = Field(..., description="The character's name.")
    summary: str = Field(default="", description="The character's summary/description (V1 field).")
    personality: str = Field(default="", description="The character's personality (V1 field).")
    scenario: str = Field(default="", description="The character's scenario (V1 field).")
    greeting_message: str = Field(default="", description="The character's first message/greeting (V1 field).")
    example_messages: str = Field(default="", description="Example dialogue messages (V1 field).")
    image_path: Optional[str] = Field(None, description="Path to the associated image file.")
    created_time: Optional[int] = Field(None, description="Creation timestamp (milliseconds since epoch).")
    
    # V2/V3 fields
    creator_notes: Optional[str] = Field(None, description="Notes from the creator.")
    system_prompt: Optional[str] = Field(None, description="System prompt/instruction.")
    post_history_instructions: Optional[str] = Field(None, description="Instructions for post-history processing.")
    alternate_greetings: Optional[List[str]] = Field(None, description="Alternate greeting messages.")
    tags: Optional[List[str]] = Field(None, description="Character tags.")
    creator: Optional[str] = Field(None, description="The creator's name.")
    character_version: Optional[str] = Field(None, description="Character card version.")
    extensions: Optional[dict] = Field(None, description="Arbitrary extensions data (JSON object).")
    character_book: Optional[dict] = Field(None, description="Character book/lorebook data (JSON object).")


class AISourceEditJobPayload(BaseModel):
    """
    Payload for requesting AI editing of source content via a background job.
    """

    source_id: UUID = Field(..., description="The ID of the ProjectSource being edited.")
    original_content: str = Field(..., description="The content segment to be edited.")
    edit_instruction: str = Field(..., description="The user's instruction for the AI edit.")
    full_content_context: Optional[str] = Field(
        None, description="The full source content, used as context if only a segment is being edited."
    )


class AISourceEditJobResult(BaseModel):
    """
    Result of the AI source edit job.
    """

    source_id: UUID = Field(..., description="The ID of the ProjectSource that was edited.")
    edited_content: str = Field(..., description="The content after AI editing.")

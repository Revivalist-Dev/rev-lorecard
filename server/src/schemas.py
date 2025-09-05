from pydantic import BaseModel, Field
from typing import List, Optional


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

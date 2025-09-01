from pydantic import BaseModel, Field
from typing import List


class SelectorResponse(BaseModel):
    """
    Represents the expected JSON structure for a selector generation response.
    """

    selectors: List[str] = Field(
        ...,
        description="A list of CSS selectors that target the desired links on the page.",
    )


class LorebookEntryResponse(BaseModel):
    """
    Represents the expected JSON structure for a lorebook entry.
    """

    title: str = Field(..., description="The main title of the lore entry.")
    content: str = Field(..., description="The summarized body of the lore entry.")
    keywords: List[str] = Field(
        ...,
        description="A list of keywords that can be used to trigger this entry in a roleplay application.",
    )


class SearchParamsResponse(BaseModel):
    """
    Represents the expected JSON structure for a search params generation response.
    """

    purpose: str = Field(..., description="Clear statement based on request type.")
    extraction_notes: str = Field(..., description="Guidelines for extraction.")
    criteria: str = Field(..., description="Simple validation requirements.")

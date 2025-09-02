from enum import Enum
import json
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from db.connection import execute_query, fetch_query, fetchrow_query
from datetime import datetime
from db.common import PaginatedResponse, PaginationMeta


class AiProviderConfig(BaseModel):
    """Configuration for the LLM API provider."""

    api_provider: str = Field(
        ...,
        min_length=1,
        description="The API service to use (e.g., 'openrouter', 'openai').",
    )
    model_name: str = Field(
        ...,
        min_length=1,
        description="The specific model identifier (e.g., 'google/gemini-2.5-flash').",
    )
    model_parameters: Dict[str, Any] = Field(
        ...,
        description='A JSON object for model settings like `{"temperature": 1.0, "top_p": 0.9}`.',
    )


class SearchParams(BaseModel):
    purpose: str
    extraction_notes: str
    criteria: str


class ProjectTemplates(BaseModel):
    """Jinja templates for various tasks."""

    selector_generation: str = Field(
        description="The prompt used to instruct an LLM to analyze HTML and return a CSS selector."
    )
    entry_creation: str = Field(
        description="The prompt used to instruct an LLM to process a scraped web page into a structured lorebook entry."
    )
    search_params_generation: str = Field(
        description="The prompt used to instruct an LLM to generate search parameters from a user prompt."
    )


class ProjectStatus(str, Enum):
    draft = "draft"
    search_params_generated = "search_params_generated"
    selector_generated = "selector_generated"
    links_extracted = "links_extracted"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class CreateProject(BaseModel):
    id: str
    name: str
    source_url: Optional[str] = None
    prompt: Optional[str] = None
    templates: ProjectTemplates
    ai_provider_config: AiProviderConfig
    requests_per_minute: int = 15


class UpdateProject(BaseModel):
    name: Optional[str] = None
    source_url: Optional[str] = None
    link_extraction_selector: Optional[list[str]] = None
    templates: Optional[ProjectTemplates] = None
    ai_provider_config: Optional[AiProviderConfig] = None
    requests_per_minute: Optional[int] = None
    status: Optional[ProjectStatus] = None
    prompt: Optional[str] = None
    search_params: Optional[SearchParams] = None


class Project(CreateProject):
    link_extraction_selector: Optional[list[str]] = None
    search_params: Optional[SearchParams] = None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


async def create_project(project: CreateProject) -> Project:
    query = """
        INSERT INTO "Project" (id, name, source_url, prompt, templates, ai_provider_config, requests_per_minute)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        project.id,
        project.name,
        project.source_url,
        project.prompt,
        json.dumps(project.templates.model_dump()),
        json.dumps(project.ai_provider_config.model_dump()),
        project.requests_per_minute,
    )
    await execute_query(query, params)
    return await get_project(project.id)  # pyright: ignore[reportReturnType]


async def get_project(project_id: str) -> Project | None:
    """Retrieve a project by its ID."""
    query = 'SELECT * FROM "Project" WHERE id = %s'
    result = await fetchrow_query(query, (project_id,))
    if result and result.get("search_params"):
        result["search_params"] = SearchParams.model_validate(result["search_params"])
    return Project(**result) if result else None


async def count_projects() -> int:
    """Count all projects."""
    query = 'SELECT COUNT(*) FROM "Project"'
    result = await fetchrow_query(query)
    return result["count"] if result else 0


async def list_projects_paginated(
    limit: int = 50, offset: int = 0
) -> PaginatedResponse[Project]:
    """List all projects with pagination."""
    query = 'SELECT * FROM "Project" ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await fetch_query(query, (limit, offset))
    projects = [Project(**row) for row in results] if results else []
    total_items = await count_projects()
    current_page = offset // limit + 1

    return PaginatedResponse(
        data=projects,
        meta=PaginationMeta(
            current_page=current_page,
            per_page=limit,
            total_items=total_items,
        ),
    )


async def update_project(
    project_id: str, project_update: UpdateProject
) -> Project | None:
    update_data = project_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_project(project_id)

    set_clause_parts = []
    params = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        if key in ["ai_provider_config", "templates", "search_params"]:
            params.append(json.dumps(value))
        elif isinstance(value, Enum):
            params.append(value.value)
        else:
            params.append(value)

    if not set_clause_parts:
        return await get_project(project_id)

    params.append(project_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "Project" SET {set_clause}, updated_at = NOW() WHERE id = %s'

    await execute_query(query, params)
    return await get_project(project_id)


async def delete_project(project_id: str):
    """Delete a project from the database."""
    query = 'DELETE FROM "Project" WHERE id = %s'
    await execute_query(query, (project_id,))

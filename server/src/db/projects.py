from enum import Enum
import json
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field
from db.connection import get_db_connection
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
    prompt: Optional[str] = None
    templates: ProjectTemplates
    ai_provider_config: AiProviderConfig
    requests_per_minute: int = 15


class UpdateProject(BaseModel):
    name: Optional[str] = None
    templates: Optional[ProjectTemplates] = None
    ai_provider_config: Optional[AiProviderConfig] = None
    requests_per_minute: Optional[int] = None
    status: Optional[ProjectStatus] = None
    prompt: Optional[str] = None
    search_params: Optional[SearchParams] = None


class Project(CreateProject):
    search_params: Optional[SearchParams] = None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


def _deserialize_project(row: Optional[Dict[str, Any]]) -> Optional[Project]:
    """
    Takes a raw DB row and correctly deserializes JSON string fields
    before validating with the Pydantic model.
    """
    if not row:
        return None

    # These are the keys that are stored as JSON strings in SQLite
    json_keys = ["search_params", "templates", "ai_provider_config"]

    for key in json_keys:
        if key in row and isinstance(row[key], str):
            try:
                # This correctly handles 'null', '{}', '[]', etc.
                row[key] = json.loads(row[key])
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, it might be an empty string or malformed data.
                # Setting it to None is a safe fallback.
                row[key] = None

    return Project(**row)


async def create_project(project: CreateProject) -> Project:
    db = await get_db_connection()
    query = """
        INSERT INTO "Project" (id, name, prompt, templates, ai_provider_config, requests_per_minute)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    params = (
        project.id,
        project.name,
        project.prompt,
        json.dumps(project.templates.model_dump()),
        json.dumps(project.ai_provider_config.model_dump()),
        project.requests_per_minute,
    )
    result = await db.fetch_one(query, params)
    if not result:
        raise Exception("Failed to create project")

    deserialized_project = _deserialize_project(result)
    if not deserialized_project:
        raise Exception("Failed to deserialize created project")
    return deserialized_project


async def get_project(project_id: str) -> Project | None:
    """Retrieve a project by its ID."""
    db = await get_db_connection()
    query = 'SELECT * FROM "Project" WHERE id = %s'
    result = await db.fetch_one(query, (project_id,))
    return _deserialize_project(result)


async def count_projects() -> int:
    """Count all projects."""
    db = await get_db_connection()
    query = 'SELECT COUNT(*) as count FROM "Project"'
    result = await db.fetch_one(query)
    return result["count"] if result and "count" in result else 0


async def list_projects_paginated(
    limit: int = 50, offset: int = 0
) -> PaginatedResponse[Project]:
    """List all projects with pagination."""
    db = await get_db_connection()
    query = 'SELECT * FROM "Project" ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await db.fetch_all(query, (limit, offset))
    projects = [_deserialize_project(row) for row in results if row]
    projects = [p for p in projects if p]
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
    db = await get_db_connection()
    update_data = project_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_project(project_id)

    set_clause_parts = []
    params: List[Any] = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        if key in ["ai_provider_config", "templates", "search_params"]:
            if hasattr(value, "model_dump"):
                params.append(json.dumps(value.model_dump()))
            else:
                params.append(json.dumps(value))
        elif isinstance(value, Enum):
            params.append(value.value)
        else:
            params.append(value)

    if not set_clause_parts:
        return await get_project(project_id)

    params.append(project_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "Project" SET {set_clause} WHERE id = %s RETURNING *'

    result = await db.fetch_one(query, tuple(params))
    return _deserialize_project(result)


async def delete_project(project_id: str):
    """Delete a project from the database."""
    db = await get_db_connection()
    query = 'DELETE FROM "Project" WHERE id = %s'
    await db.execute(query, (project_id,))

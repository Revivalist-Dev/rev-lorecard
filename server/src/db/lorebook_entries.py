import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from db.connection import execute_query, fetch_query, fetchrow_query
from pydantic import BaseModel
from db.common import PaginatedResponse, PaginationMeta


class CreateLorebookEntry(BaseModel):
    """Model for creating a new lorebook entry."""

    project_id: str
    title: str
    content: str
    keywords: List[str]
    source_url: str


class UpdateLorebookEntry(BaseModel):
    """Model for updating an existing lorebook entry."""

    title: Optional[str] = None
    content: Optional[str] = None
    keywords: Optional[List[str]] = None


class LorebookEntry(CreateLorebookEntry):
    """Represents a final, structured lorebook entry."""

    id: UUID
    created_at: datetime
    updated_at: datetime


async def create_lorebook_entry(
    entry: CreateLorebookEntry,
) -> LorebookEntry:
    """Create a new lorebook entry and return it."""
    entry_id = uuid4()
    query = """
        INSERT INTO "LorebookEntry" (id, project_id, title, content, keywords, source_url)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = (
        entry_id,
        entry.project_id,
        entry.title,
        entry.content,
        json.dumps(entry.keywords),
        entry.source_url,
    )
    await execute_query(query, params)
    return await get_lorebook_entry(entry_id)  # pyright: ignore[reportReturnType]


async def get_lorebook_entry(entry_id: UUID) -> LorebookEntry | None:
    """Retrieve a lorebook entry by its ID."""
    query = 'SELECT * FROM "LorebookEntry" WHERE id = %s'
    result = await fetchrow_query(query, (entry_id,))
    return LorebookEntry(**result) if result else None


async def count_entries_by_project(project_id: str) -> int:
    """Count all lorebook entries for a given project."""
    query = 'SELECT COUNT(*) FROM "LorebookEntry" WHERE project_id = %s'
    result = await fetchrow_query(query, (project_id,))
    return result["count"] if result else 0


async def list_entries_by_project_paginated(
    project_id: str, limit: int = 100, offset: int = 0
) -> PaginatedResponse[LorebookEntry]:
    """Retrieve all lorebook entries for a specific project with pagination."""
    query = 'SELECT * FROM "LorebookEntry" WHERE project_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await fetch_query(query, (project_id, limit, offset))
    entries = [LorebookEntry(**row) for row in results] if results else []
    total_items = await count_entries_by_project(project_id)
    current_page = offset // limit + 1

    return PaginatedResponse(
        data=entries,
        meta=PaginationMeta(
            current_page=current_page,
            per_page=limit,
            total_items=total_items,
        ),
    )


async def list_all_entries_by_project(project_id: str) -> List[LorebookEntry]:
    """Retrieve all lorebook entries for a specific project."""
    query = (
        'SELECT * FROM "LorebookEntry" WHERE project_id = %s ORDER BY created_at DESC'
    )
    results = await fetch_query(query, (project_id,))
    return [LorebookEntry(**row) for row in results] if results else []


async def update_lorebook_entry(
    entry_id: UUID, entry_update: UpdateLorebookEntry
) -> LorebookEntry | None:
    """Update a lorebook entry's title, content, or keywords."""
    update_data = entry_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_lorebook_entry(entry_id)

    set_clause_parts = []
    params = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        if key == "keywords":
            params.append(json.dumps(value))
        else:
            params.append(value)

    if not set_clause_parts:
        return await get_lorebook_entry(entry_id)

    params.append(entry_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "LorebookEntry" SET {set_clause} WHERE id = %s'

    await execute_query(query, params)
    return await get_lorebook_entry(entry_id)


async def delete_lorebook_entry(entry_id: UUID):
    """Delete a lorebook entry from the database."""
    query = 'DELETE FROM "LorebookEntry" WHERE id = %s'
    await execute_query(query, (entry_id,))

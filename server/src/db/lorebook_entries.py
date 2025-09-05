import json
from datetime import datetime
from typing import List, Optional, Any
from uuid import UUID, uuid4

from db.connection import get_db_connection
from pydantic import BaseModel
from db.common import PaginatedResponse, PaginationMeta
from db.database import AsyncDBTransaction, DatabaseType


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
    entry: CreateLorebookEntry, tx: Optional[AsyncDBTransaction] = None
) -> LorebookEntry:
    """Create a new lorebook entry and return it."""
    db = tx or await get_db_connection()
    query = """
        INSERT INTO "LorebookEntry" (id, project_id, title, content, keywords, source_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    params = (
        uuid4(),
        entry.project_id,
        entry.title,
        entry.content,
        json.dumps(entry.keywords),
        entry.source_url,
    )
    result = await db.execute_and_fetch_one(query, params)
    if not result:
        raise Exception("Failed to create lorebook entry")
    return LorebookEntry(**result)


async def get_lorebook_entry(entry_id: UUID) -> LorebookEntry | None:
    """Retrieve a lorebook entry by its ID."""
    db = await get_db_connection()
    query = 'SELECT * FROM "LorebookEntry" WHERE id = %s'
    result = await db.fetch_one(query, (entry_id,))
    return LorebookEntry(**result) if result else None


async def count_entries_by_project(
    project_id: str, search_query: Optional[str] = None
) -> int:
    """Count all lorebook entries for a given project, with an optional search filter."""
    db = await get_db_connection()
    base_query = 'SELECT COUNT(*) as count FROM "LorebookEntry" WHERE project_id = %s'
    params: List[Any] = [project_id]

    if search_query:
        search_term = f"%{search_query}%"
        db_type = db.__class__.__name__
        like_operator = "ILIKE" if db_type == "PostgresDB" else "LIKE"
        keywords_field = "keywords::text" if db_type == "PostgresDB" else "keywords"

        base_query += f" AND (title {like_operator} %s OR {keywords_field} {like_operator} %s OR content {like_operator} %s)"
        params.extend([search_term, search_term, search_term])

    result = await db.fetch_one(base_query, tuple(params))
    return result["count"] if result and "count" in result else 0


async def list_entries_by_project_paginated(
    project_id: str,
    limit: int = 100,
    offset: int = 0,
    search_query: Optional[str] = None,
) -> PaginatedResponse[LorebookEntry]:
    """Retrieve all lorebook entries for a specific project with pagination and optional search."""
    db = await get_db_connection()
    base_query = 'SELECT * FROM "LorebookEntry" WHERE project_id = %s'
    params: List[Any] = [project_id]

    if search_query:
        search_term = f"%{search_query}%"
        db_type = db.database_type()
        like_operator = "ILIKE" if db_type == DatabaseType.POSTGRES else "LIKE"
        keywords_field = (
            "keywords::text" if db_type == DatabaseType.POSTGRES else "keywords"
        )
        base_query += f" AND (title {like_operator} %s OR {keywords_field} {like_operator} %s OR content {like_operator} %s)"
        params.extend([search_term, search_term, search_term])

    base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    results = await db.fetch_all(base_query, tuple(params))
    entries = [LorebookEntry(**row) for row in results] if results else []

    total_items = await count_entries_by_project(project_id, search_query)
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
    db = await get_db_connection()
    query = (
        'SELECT * FROM "LorebookEntry" WHERE project_id = %s ORDER BY created_at DESC'
    )
    results = await db.fetch_all(query, (project_id,))
    return [LorebookEntry(**row) for row in results] if results else []


async def update_lorebook_entry(
    entry_id: UUID, entry_update: UpdateLorebookEntry
) -> LorebookEntry | None:
    """Update a lorebook entry's title, content, or keywords."""
    db = await get_db_connection()
    update_data = entry_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_lorebook_entry(entry_id)

    set_clause_parts = []
    params: List[Any] = []
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
    query = f'UPDATE "LorebookEntry" SET {set_clause} WHERE id = %s RETURNING *'

    result = await db.execute_and_fetch_one(query, tuple(params))
    return LorebookEntry(**result) if result else None


async def delete_lorebook_entry(entry_id: UUID):
    """Delete a lorebook entry from the database."""
    db = await get_db_connection()
    query = 'DELETE FROM "LorebookEntry" WHERE id = %s'
    await db.execute(query, (entry_id,))

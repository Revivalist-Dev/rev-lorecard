from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from db.connection import get_db_connection
from pydantic import BaseModel
from db.common import PaginatedResponse, PaginationMeta
from db.database import AsyncDBTransaction


class LinkStatus(str, Enum):
    """Enum for the lifecycle state of a link."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class CreateLink(BaseModel):
    """Model for creating a new link."""

    project_id: str
    url: str


class UpdateLink(BaseModel):
    """Model for updating an existing link."""

    status: Optional[LinkStatus] = None
    error_message: Optional[str] = None
    skip_reason: Optional[str] = None
    lorebook_entry_id: Optional[UUID] = None
    raw_content: Optional[str] = None


class Link(CreateLink):
    """Represents a single URL to be processed."""

    id: UUID
    status: LinkStatus
    error_message: Optional[str] = None
    skip_reason: Optional[str] = None
    lorebook_entry_id: Optional[UUID] = None
    created_at: datetime
    raw_content: Optional[str] = None


async def create_links(links: List[CreateLink], tx: AsyncDBTransaction) -> List[Link]:
    """
    Batch insert a list of links for a project.
    This function uses a transaction to ensure all links are inserted or none are.
    Returns the list of created links.
    """
    created_links: List[Link] = []
    query = """
        INSERT INTO "Link" (id, project_id, url)
        VALUES (%s, %s, %s)
        ON CONFLICT (project_id, url) DO NOTHING
        RETURNING *
    """
    for link in links:
        result = await tx.execute_and_fetch_one(
            query, (uuid4(), link.project_id, link.url)
        )
        if result:
            created_links.append(Link(**result))
    return created_links


async def get_link(
    link_id: UUID, tx: Optional[AsyncDBTransaction] = None
) -> Link | None:
    """Retrieve a link by its ID."""
    db = tx or await get_db_connection()
    query = 'SELECT * FROM "Link" WHERE id = %s'
    result = await db.fetch_one(query, (link_id,))
    return Link(**result) if result else None


async def get_existing_links_by_urls(
    project_id: str, urls: List[str], tx: Optional[AsyncDBTransaction] = None
) -> List[str]:
    """
    Given a list of URLs, return the subset that already exists for the project.
    """
    if not urls:
        return []
    db = tx or await get_db_connection()
    # Create a placeholder string like (%s, %s, %s)
    placeholders = ", ".join(["%s"] * len(urls))
    query = f'SELECT url FROM "Link" WHERE project_id = %s AND url IN ({placeholders})'
    params = (project_id, *urls)
    results = await db.fetch_all(query, params)  # pyright: ignore[reportArgumentType]
    return [row["url"] for row in results] if results else []


async def count_links_by_project(project_id: str) -> int:
    """Count all links for a given project."""
    db = await get_db_connection()
    query = 'SELECT COUNT(*) as count FROM "Link" WHERE project_id = %s'
    result = await db.fetch_one(query, (project_id,))
    return result["count"] if result and "count" in result else 0


async def count_processable_links_by_project(project_id: str) -> int:
    """Count all processable (pending or failed) links for a given project."""
    db = await get_db_connection()
    query = "SELECT COUNT(*) as count FROM \"Link\" WHERE project_id = %s AND (status = 'pending' OR status = 'failed')"
    result = await db.fetch_one(query, (project_id,))
    return result["count"] if result and "count" in result else 0


async def get_processable_links_for_project(
    project_id: str, tx: Optional[AsyncDBTransaction] = None
) -> List[Link]:
    """Retrieve all processable (pending or failed) links for a specific project."""
    db = tx or await get_db_connection()
    query = "SELECT * FROM \"Link\" WHERE project_id = %s AND (status = 'pending' OR status = 'failed')"
    results = await db.fetch_all(query, (project_id,))
    return [Link(**row) for row in results] if results else []


async def list_links_by_project_paginated(
    project_id: str, limit: int = 100, offset: int = 0
) -> PaginatedResponse[Link]:
    """Retrieve all links associated with a specific project with pagination."""
    db = await get_db_connection()
    query = 'SELECT * FROM "Link" WHERE project_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await db.fetch_all(query, (project_id, limit, offset))
    links = [Link(**row) for row in results] if results else []
    total_items = await count_links_by_project(project_id)
    current_page = offset // limit + 1

    return PaginatedResponse(
        data=links,
        meta=PaginationMeta(
            current_page=current_page,
            per_page=limit,
            total_items=total_items,
        ),
    )


async def update_link(
    link_id: UUID, link_update: UpdateLink, tx: Optional[AsyncDBTransaction] = None
) -> Link | None:
    """Update a link's status, error message, or lorebook entry ID."""
    db = tx or await get_db_connection()
    update_data = link_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_link(link_id)

    set_clause_parts = []
    params = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        params.append(value)

    if not set_clause_parts:
        return await get_link(link_id, tx=tx)

    params.append(link_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "Link" SET {set_clause} WHERE id = %s'

    await db.execute(query, tuple(params))
    return await get_link(link_id, tx=tx)


async def reset_processing_links_to_pending(
    tx: Optional[AsyncDBTransaction] = None,
) -> None:
    db = tx or await get_db_connection()
    query = "UPDATE \"Link\" SET status = 'pending' WHERE status = 'processing'"
    await db.execute(query)

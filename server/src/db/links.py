from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from db.connection import execute_query, fetch_query, fetchrow_query, get_pool
from pydantic import BaseModel
from db.common import PaginatedResponse, PaginationMeta


class LinkStatus(str, Enum):
    """Enum for the lifecycle state of a link."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class CreateLink(BaseModel):
    """Model for creating a new link."""

    project_id: str
    url: str


class UpdateLink(BaseModel):
    """Model for updating an existing link."""

    status: Optional[LinkStatus] = None
    error_message: Optional[str] = None
    lorebook_entry_id: Optional[UUID] = None
    raw_content: Optional[str] = None


class Link(CreateLink):
    """Represents a single URL to be processed."""

    id: UUID
    status: LinkStatus
    error_message: Optional[str] = None
    lorebook_entry_id: Optional[UUID] = None
    created_at: datetime
    raw_content: Optional[str] = None


async def create_links(links: List[CreateLink]) -> List[Link]:
    """
    Batch insert a list of links for a project.
    This function uses a transaction to ensure all links are inserted or none are.
    Returns the list of created links.
    """
    pool = await get_pool()
    created_links: List[Link] = []
    async with pool.connection() as conn:
        async with conn.transaction():
            query = """
                INSERT INTO "Link" (id, project_id, url)
                VALUES (%s, %s, %s)
                RETURNING *
            """
            for link in links:
                result = await fetchrow_query(
                    query, (uuid4(), link.project_id, link.url), conn=conn
                )
                if result:
                    created_links.append(Link(**result))
    return created_links


async def get_link(link_id: UUID) -> Link | None:
    """Retrieve a link by its ID."""
    query = 'SELECT * FROM "Link" WHERE id = %s'
    result = await fetchrow_query(query, (link_id,))
    return Link(**result) if result else None


async def count_links_by_project(project_id: str) -> int:
    """Count all links for a given project."""
    query = 'SELECT COUNT(*) FROM "Link" WHERE project_id = %s'
    result = await fetchrow_query(query, (project_id,))
    return result["count"] if result else 0


async def get_pending_links_for_project(project_id: str) -> List[Link]:
    """Retrieve all pending links for a specific project."""
    query = "SELECT * FROM \"Link\" WHERE project_id = %s AND status = 'pending'"
    results = await fetch_query(query, (project_id,))
    return [Link(**row) for row in results] if results else []


async def list_links_by_project_paginated(
    project_id: str, limit: int = 100, offset: int = 0
) -> PaginatedResponse[Link]:
    """Retrieve all links associated with a specific project with pagination."""
    query = 'SELECT * FROM "Link" WHERE project_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await fetch_query(query, (project_id, limit, offset))
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


async def update_link(link_id: UUID, link_update: UpdateLink) -> Link | None:
    """Update a link's status, error message, or lorebook entry ID."""
    update_data = link_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_link(link_id)

    set_clause_parts = []
    params = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        params.append(value)

    if not set_clause_parts:
        return await get_link(link_id)

    params.append(link_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "Link" SET {set_clause} WHERE id = %s'

    await execute_query(query, params)
    return await get_link(link_id)

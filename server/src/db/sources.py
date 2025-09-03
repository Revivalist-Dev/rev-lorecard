from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID, uuid4

from db.connection import get_db_connection
from pydantic import BaseModel


class ProjectSource(BaseModel):
    id: UUID
    project_id: str
    url: str
    link_extraction_selector: Optional[List[str]] = None
    link_extraction_pagination_selector: Optional[str] = None
    max_pages_to_crawl: int = 20
    last_crawled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CreateProjectSource(BaseModel):
    project_id: str
    url: str
    max_pages_to_crawl: int = 20


class UpdateProjectSource(BaseModel):
    url: Optional[str] = None
    link_extraction_selector: Optional[List[str]] = None
    link_extraction_pagination_selector: Optional[str] = None
    max_pages_to_crawl: Optional[int] = None
    last_crawled_at: Optional[datetime] = None


async def create_project_source(source: CreateProjectSource) -> ProjectSource:
    db = await get_db_connection()
    source_id = uuid4()
    query = """
        INSERT INTO "ProjectSource" (id, project_id, url, max_pages_to_crawl)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """
    params = (
        source_id,
        source.project_id,
        source.url,
        source.max_pages_to_crawl,
    )
    result = await db.fetch_one(query, params)
    if not result:
        raise Exception("Failed to create project source")
    return ProjectSource(**result)


async def get_project_source(source_id: UUID) -> ProjectSource | None:
    db = await get_db_connection()
    query = 'SELECT * FROM "ProjectSource" WHERE id = %s'
    result = await db.fetch_one(query, (source_id,))
    return ProjectSource(**result) if result else None


async def list_sources_by_project(project_id: str) -> List[ProjectSource]:
    db = await get_db_connection()
    query = (
        'SELECT * FROM "ProjectSource" WHERE project_id = %s ORDER BY created_at ASC'
    )
    results = await db.fetch_all(query, (project_id,))
    return [ProjectSource(**row) for row in results] if results else []


async def update_project_source(
    source_id: UUID, source_update: UpdateProjectSource
) -> ProjectSource | None:
    db = await get_db_connection()
    update_data = source_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_project_source(source_id)

    set_clause_parts = []
    params: List[Any] = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        params.append(value)

    params.append(source_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "ProjectSource" SET {set_clause} WHERE id = %s RETURNING *'

    result = await db.fetch_one(query, tuple(params))
    return ProjectSource(**result) if result else None


async def delete_project_source(source_id: UUID) -> None:
    db = await get_db_connection()
    query = 'DELETE FROM "ProjectSource" WHERE id = %s'
    await db.execute(query, (source_id,))

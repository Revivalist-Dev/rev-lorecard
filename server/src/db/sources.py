from datetime import datetime
from typing import Any, List, Literal, Optional
from uuid import UUID, uuid4
from logging_config import get_logger # Added for logging

SourceType = Literal["web_url", "user_text_file", "character_card"]

from db.connection import get_db_connection
from pydantic import BaseModel

from db.database import AsyncDBTransaction

ContentType = Literal["html", "markdown"]


class ProjectSource(BaseModel):
    id: UUID
    project_id: str
    source_type: SourceType = "web_url"
    url: str
    link_extraction_selector: Optional[List[str]] = None
    link_extraction_pagination_selector: Optional[str] = None
    url_exclusion_patterns: Optional[List[str]] = None
    max_pages_to_crawl: int = 20
    max_crawl_depth: int = 1
    last_crawled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    raw_content: Optional[str] = None
    content_type: Optional[ContentType] = None
    content_char_count: Optional[int] = None


class CreateProjectSource(BaseModel):
    project_id: str
    source_type: SourceType = "web_url"
    url: str
    raw_content: Optional[str] = None # For user_text_file
    max_pages_to_crawl: int = 20
    max_crawl_depth: int = 1
    url_exclusion_patterns: Optional[List[str]] = None


class UpdateProjectSource(BaseModel):
    source_type: Optional[SourceType] = None
    url: Optional[str] = None
    raw_content: Optional[str] = None # For user_text_file
    link_extraction_selector: Optional[List[str]] = None
    link_extraction_pagination_selector: Optional[str] = None
    url_exclusion_patterns: Optional[List[str]] = None
    max_pages_to_crawl: Optional[int] = None
    max_crawl_depth: Optional[int] = None
    last_crawled_at: Optional[datetime] = None
    content_type: Optional[ContentType] = None
    content_char_count: Optional[int] = None


async def create_project_source(
    source: CreateProjectSource, tx: Optional[AsyncDBTransaction] = None
) -> ProjectSource:
    db = tx or await get_db_connection()
    source_id = uuid4()

    # Set last_crawled_at and content_char_count if it's a user_text_file with content
    last_crawled_at = None
    content_char_count = None
    content_type = None
    if source.source_type == "user_text_file" and source.raw_content is not None:
        last_crawled_at = datetime.now()
        content_char_count = len(source.raw_content)
        content_type = "markdown" # Assuming user text is markdown/plain text

    query = """
        INSERT INTO "ProjectSource" (id, project_id, source_type, url, raw_content, max_pages_to_crawl, max_crawl_depth, url_exclusion_patterns, last_crawled_at, content_char_count, content_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    params = (
        source_id,
        source.project_id,
        source.source_type,
        source.url,
        source.raw_content,
        source.max_pages_to_crawl,
        source.max_crawl_depth,
        source.url_exclusion_patterns,
        last_crawled_at,
        content_char_count,
        content_type,
    )
    result = await db.execute_and_fetch_one(query, params)
    if not result:
        raise Exception("Failed to create project source")
    return ProjectSource(**result)


async def get_project_source(
    source_id: UUID, tx: Optional[AsyncDBTransaction] = None
) -> ProjectSource | None:
    db = tx or await get_db_connection()
    query = 'SELECT * FROM "ProjectSource" WHERE id = %s'
    result = await db.fetch_one(query, (source_id,))
    return ProjectSource(**result) if result else None


async def get_project_source_by_url(
    project_id: str, url: str, tx: AsyncDBTransaction
) -> ProjectSource | None:
    """Retrieve a project source by its URL within a transaction."""
    query = 'SELECT * FROM "ProjectSource" WHERE project_id = %s AND url = %s'
    result = await tx.fetch_one(query, (project_id, url))
    return ProjectSource(**result) if result else None


async def list_sources_by_project(
    project_id: str, include_content: bool = False
) -> List[ProjectSource]:
    db = await get_db_connection()
    if include_content:
        # Select all columns when content is requested
        query = 'SELECT * FROM "ProjectSource" WHERE project_id = %s ORDER BY created_at ASC'
    else:
        # Exclude raw_content for performance in list views
        query = (
            "SELECT id, project_id, source_type, url, link_extraction_selector, link_extraction_pagination_selector, "
            "url_exclusion_patterns, max_pages_to_crawl, max_crawl_depth, last_crawled_at, created_at, updated_at, "
            "content_type, content_char_count "
            'FROM "ProjectSource" WHERE project_id = %s ORDER BY created_at ASC'
        )
    results = await db.fetch_all(query, (project_id,))
    return [ProjectSource(**row) for row in results] if results else []


async def update_project_source(
    source_id: UUID,
    source_update: UpdateProjectSource,
    tx: Optional[AsyncDBTransaction] = None,
) -> ProjectSource | None:
    db = tx or await get_db_connection()
    update_data = source_update.model_dump(exclude_unset=True)
    
    # Handle raw_content update: recalculate char count and set updated_at
    if "raw_content" in update_data:
        raw_content = update_data["raw_content"]
        update_data["content_char_count"] = len(raw_content) if raw_content is not None else None
        # If content is updated, we should also update the last_crawled_at timestamp
        # to reflect that the content is fresh (either scraped or manually edited).
        update_data["last_crawled_at"] = datetime.now()
        
        # Ensure content_type is set if raw_content is set and content_type is not explicitly provided
        if "content_type" not in update_data and raw_content is not None:
            update_data["content_type"] = "markdown" # Default to markdown for manual edits

    if not update_data:
        return await get_project_source(source_id, tx=tx)

    set_clause_parts = []
    params: List[Any] = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        params.append(value)

    params.append(source_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "ProjectSource" SET {set_clause} WHERE id = %s RETURNING *'

    # Debugging: Log the query and parameters
    from logging_config import get_logger
    logger = get_logger(__name__)
    logger.debug(f"Update ProjectSource Query: {query}")
    logger.debug(f"Update ProjectSource Params: {params}")

    result = await db.execute_and_fetch_one(query, tuple(params))
    logger.debug(f"Update ProjectSource Result: {result}")
    return ProjectSource(**result) if result else None


async def delete_project_source(source_id: UUID) -> None:
    db = await get_db_connection()
    query = 'DELETE FROM "ProjectSource" WHERE id = %s'
    await db.execute(query, (source_id,))


async def delete_project_sources_bulk(
    project_id: str, source_ids: List[UUID], tx: Optional[AsyncDBTransaction] = None
) -> None:
    """Deletes multiple project sources in a single operation."""
    db = tx or await get_db_connection()
    if not source_ids:
        return

    placeholders = ", ".join(["%s"] * len(source_ids))
    query = (
        f'DELETE FROM "ProjectSource" WHERE project_id = %s AND id IN ({placeholders})'
    )
    params = (project_id, *source_ids)
    await db.execute(query, params)

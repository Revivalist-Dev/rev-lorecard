from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from db.connection import get_db_connection
from pydantic import BaseModel

from db.database import AsyncDBTransaction


class ProjectSourceHierarchy(BaseModel):
    id: UUID
    project_id: str
    parent_source_id: UUID
    child_source_id: UUID
    created_at: datetime


async def add_source_child_relationship(
    project_id: str,
    parent_source_id: UUID,
    child_source_id: UUID,
    tx: AsyncDBTransaction,
) -> ProjectSourceHierarchy:
    """Create a new parent-child relationship between two sources."""
    query = """
        INSERT INTO "ProjectSourceHierarchy" (id, project_id, parent_source_id, child_source_id)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (parent_source_id, child_source_id) DO NOTHING
        RETURNING *
    """
    params = (uuid4(), project_id, parent_source_id, child_source_id)
    result = await tx.execute_and_fetch_one(query, params)
    if not result:
        # If the relationship already exists, fetch it to return.
        existing_query = 'SELECT * FROM "ProjectSourceHierarchy" WHERE parent_source_id = %s AND child_source_id = %s'
        existing_result = await tx.fetch_one(
            existing_query, (parent_source_id, child_source_id)
        )
        if not existing_result:
            raise Exception("Failed to create or find source hierarchy relationship")
        return ProjectSourceHierarchy(**existing_result)
    return ProjectSourceHierarchy(**result)


async def get_source_hierarchy_for_project(
    project_id: str, tx: Optional[AsyncDBTransaction] = None
) -> List[ProjectSourceHierarchy]:
    """Retrieve all hierarchy relationships for a project."""
    db = tx or await get_db_connection()
    query = 'SELECT * FROM "ProjectSourceHierarchy" WHERE project_id = %s'
    results = await db.fetch_all(query, (project_id,))
    return [ProjectSourceHierarchy(**row) for row in results] if results else []

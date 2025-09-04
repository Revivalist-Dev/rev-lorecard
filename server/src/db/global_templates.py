from datetime import datetime
from typing import Optional, List, Any

from db.common import CreateGlobalTemplate, PaginatedResponse, PaginationMeta
from db.connection import get_db_connection
from pydantic import BaseModel


class GlobalTemplate(BaseModel):
    id: str
    name: str
    content: str
    created_at: datetime
    updated_at: datetime


class UpdateGlobalTemplate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None


async def create_global_template(
    template: CreateGlobalTemplate,
) -> GlobalTemplate:
    db = await get_db_connection()
    query = """
        INSERT INTO "GlobalTemplate" (id, name, content)
        VALUES (%s, %s, %s)
        RETURNING *
    """
    params = (
        template.id,
        template.name,
        template.content,
    )
    result = await db.execute_and_fetch_one(query, params)
    if not result:
        raise Exception("Failed to create global template")
    return GlobalTemplate(**result)


async def get_global_template(template_id: str) -> GlobalTemplate | None:
    """Retrieve a global template by its ID."""
    db = await get_db_connection()
    query = 'SELECT * FROM "GlobalTemplate" WHERE id = %s'
    result = await db.fetch_one(query, (template_id,))
    return GlobalTemplate(**result) if result else None


async def count_global_templates() -> int:
    """Count all global templates."""
    db = await get_db_connection()
    query = 'SELECT COUNT(*) as count FROM "GlobalTemplate"'
    result = await db.fetch_one(query)
    return result["count"] if result and "count" in result else 0


async def list_global_templates_paginated(
    limit: int = 50, offset: int = 0
) -> PaginatedResponse[GlobalTemplate]:
    """List all global templates with pagination."""
    db = await get_db_connection()
    query = 'SELECT * FROM "GlobalTemplate" ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await db.fetch_all(query, (limit, offset))
    templates = [GlobalTemplate(**row) for row in results] if results else []
    total_items = await count_global_templates()
    current_page = offset // limit + 1

    return PaginatedResponse(
        data=templates,
        meta=PaginationMeta(
            current_page=current_page,
            per_page=limit,
            total_items=total_items,
        ),
    )


async def list_all_global_templates() -> list[GlobalTemplate]:
    """List all global templates."""
    db = await get_db_connection()
    query = 'SELECT * FROM "GlobalTemplate" ORDER BY created_at DESC'
    results = await db.fetch_all(query)
    return [GlobalTemplate(**row) for row in results] if results else []


async def update_global_template(
    template_id: str, template_update: UpdateGlobalTemplate
) -> GlobalTemplate | None:
    db = await get_db_connection()
    update_data = template_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_global_template(template_id)

    set_clause_parts = []
    params: List[Any] = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        params.append(value)

    if not set_clause_parts:
        return await get_global_template(template_id)

    params.append(template_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "GlobalTemplate" SET {set_clause} WHERE id = %s RETURNING *'

    result = await db.execute_and_fetch_one(query, tuple(params))
    return GlobalTemplate(**result) if result else None


async def delete_global_template(template_id: str):
    """Delete a global template from the database."""
    db = await get_db_connection()
    query = 'DELETE FROM "GlobalTemplate" WHERE id = %s'
    await db.execute(query, (template_id,))

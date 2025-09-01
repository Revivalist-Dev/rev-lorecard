from datetime import datetime
from typing import Optional

from db.common import PaginatedResponse, PaginationMeta
from db.connection import execute_query, fetch_query, fetchrow_query
from pydantic import BaseModel, Field


class GlobalTemplate(BaseModel):
    id: str
    name: str
    content: str
    created_at: datetime
    updated_at: datetime


class CreateGlobalTemplate(BaseModel):
    id: str = Field(..., description="The unique identifier for the template.")
    name: str = Field(..., description="The unique name for the template.")
    content: str = Field(..., description="The content of the template.")


class UpdateGlobalTemplate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None


async def create_global_template(
    template: CreateGlobalTemplate,
) -> GlobalTemplate:
    query = """
        INSERT INTO "GlobalTemplate" (id, name, content)
        VALUES (%s, %s, %s)
    """
    params = (
        template.id,
        template.name,
        template.content,
    )
    await execute_query(query, params)
    new_template = await get_global_template(template.id)
    if not new_template:
        raise Exception("Failed to retrieve newly created global template")
    return new_template


async def get_global_template(template_id: str) -> GlobalTemplate | None:
    """Retrieve a global template by its ID."""
    query = 'SELECT * FROM "GlobalTemplate" WHERE id = %s'
    result = await fetchrow_query(query, (template_id,))
    return GlobalTemplate(**result) if result else None


async def count_global_templates() -> int:
    """Count all global templates."""
    query = 'SELECT COUNT(*) FROM "GlobalTemplate"'
    result = await fetchrow_query(query)
    return result["count"] if result else 0


async def list_global_templates_paginated(
    limit: int = 50, offset: int = 0
) -> PaginatedResponse[GlobalTemplate]:
    """List all global templates with pagination."""
    query = 'SELECT * FROM "GlobalTemplate" ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await fetch_query(query, (limit, offset))
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
    query = 'SELECT * FROM "GlobalTemplate" ORDER BY created_at DESC'
    results = await fetch_query(query)
    return [GlobalTemplate(**row) for row in results] if results else []


async def update_global_template(
    template_id: str, template_update: UpdateGlobalTemplate
) -> GlobalTemplate | None:
    update_data = template_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_global_template(template_id)

    set_clause_parts = []
    params = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        params.append(value)

    if not set_clause_parts:
        return await get_global_template(template_id)

    params.append(template_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "GlobalTemplate" SET {set_clause} WHERE id = %s'

    await execute_query(query, params)
    return await get_global_template(template_id)


async def delete_global_template(template_id: str):
    """Delete a global template from the database."""
    query = 'DELETE FROM "GlobalTemplate" WHERE id = %s'
    await execute_query(query, (template_id,))

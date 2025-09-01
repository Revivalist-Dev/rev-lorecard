import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from db.connection import execute_query, fetch_query, fetchrow_query
from db.common import PaginatedResponse, PaginationMeta
from pydantic import BaseModel


class CreateApiRequestLog(BaseModel):
    """Model for creating a new API request log entry."""

    project_id: str
    job_id: Optional[UUID] = None
    api_provider: str
    model_used: str
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    calculated_cost: Optional[float] = None
    latency_ms: int
    error: bool = False
    timestamp: datetime = datetime.now()


class ApiRequestLog(CreateApiRequestLog):
    """Represents an immutable audit record of an external API call."""

    id: UUID


async def create_api_request_log(log: CreateApiRequestLog) -> ApiRequestLog:
    """Create a new API request log."""
    log_id = uuid4()
    query = """
        INSERT INTO "ApiRequestLog" (
            id, project_id, job_id, api_provider, model_used, request,
            response, input_tokens, output_tokens, calculated_cost, latency_ms, error, timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        log_id,
        log.project_id,
        log.job_id,
        log.api_provider,
        log.model_used,
        json.dumps(log.request),
        json.dumps(log.response) if log.response else None,
        log.input_tokens,
        log.output_tokens,
        log.calculated_cost,
        log.latency_ms,
        log.error,
        log.timestamp,
    )
    await execute_query(query, params)
    return await get_api_request_log(log_id)  # pyright: ignore[reportReturnType]


async def get_api_request_log(log_id: UUID) -> ApiRequestLog | None:
    """Retrieve an API request log by its ID."""
    query = 'SELECT * FROM "ApiRequestLog" WHERE id = %s'
    result = await fetchrow_query(query, (log_id,))
    return ApiRequestLog(**result) if result else None


async def count_logs_by_project(project_id: str) -> int:
    """Count all API request logs for a specific project."""
    query = 'SELECT COUNT(*) FROM "ApiRequestLog" WHERE project_id = %s'
    result = await fetchrow_query(query, (project_id,))
    return result["count"] if result else 0


async def list_logs_by_project_paginated(
    project_id: str, limit: int = 100, offset: int = 0
) -> PaginatedResponse[ApiRequestLog]:
    """Retrieve all API request logs for a specific project with pagination."""
    query = 'SELECT * FROM "ApiRequestLog" WHERE project_id = %s ORDER BY timestamp DESC LIMIT %s OFFSET %s'
    results = await fetch_query(query, (project_id, limit, offset))
    logs = [ApiRequestLog(**row) for row in results] if results else []
    total_items = await count_logs_by_project(project_id)
    current_page = offset // limit + 1

    return PaginatedResponse(
        data=logs,
        meta=PaginationMeta(
            current_page=current_page,
            per_page=limit,
            total_items=total_items,
        ),
    )

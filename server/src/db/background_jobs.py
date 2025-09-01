from datetime import datetime
from enum import Enum
import json
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from db.connection import execute_query, fetch_query, fetchrow_query
from db.common import PaginatedResponse, PaginationMeta
from pydantic import BaseModel


class JobStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelling = "cancelling"
    canceled = "canceled"


class TaskName(str, Enum):
    GENERATE_SELECTOR = "generate_selector"
    EXTRACT_LINKS = "extract_links"
    PROCESS_PROJECT_ENTRIES = "process_project_entries"
    GENERATE_SEARCH_PARAMS = "generate_search_params"


PARALLEL_LIMITS = {
    TaskName.GENERATE_SELECTOR: 1,
    TaskName.EXTRACT_LINKS: 1,
    TaskName.PROCESS_PROJECT_ENTRIES: 1,
    TaskName.GENERATE_SEARCH_PARAMS: 1,
}


# Payloads
class GenerateSelectorPayload(BaseModel):
    pass


class ExtractLinksPayload(BaseModel):
    urls: List[str]


class ProcessProjectEntriesPayload(BaseModel):
    pass


class GenerateSearchParamsPayload(BaseModel):
    pass


TaskPayload = Union[
    GenerateSelectorPayload,
    ExtractLinksPayload,
    ProcessProjectEntriesPayload,
    GenerateSearchParamsPayload,
]


# Results
class GenerateSelectorResult(BaseModel):
    selectors: Dict[str, List[str]]


class ExtractLinksResult(BaseModel):
    links_found: int


class ProcessProjectEntriesResult(BaseModel):
    entries_created: int
    entries_failed: int


class GenerateSearchParamsResult(BaseModel):
    pass


TaskResult = Union[
    GenerateSelectorResult,
    ExtractLinksResult,
    ProcessProjectEntriesResult,
    GenerateSearchParamsResult,
]


class CreateBackgroundJob(BaseModel):
    """Model for creating a new background job."""

    task_name: TaskName
    project_id: str
    payload: TaskPayload


class UpdateBackgroundJob(BaseModel):
    """Model for updating an existing background job."""

    status: Optional[JobStatus] = None
    result: Optional[TaskResult] = None
    error_message: Optional[str] = None
    total_items: Optional[int] = None
    processed_items: Optional[int] = None
    progress: Optional[float] = None


class BackgroundJob(CreateBackgroundJob):
    """Represents a single asynchronous task."""

    id: UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result: Optional[TaskResult] = None
    error_message: Optional[str] = None
    total_items: Optional[int] = None
    processed_items: Optional[int] = None
    progress: Optional[float] = None


def _deserialize_job(db_row: Dict[str, Any]) -> BackgroundJob:
    """Deserialize a database row into a BackgroundJob model."""
    task_name = db_row["task_name"]

    payload_map = {
        TaskName.GENERATE_SELECTOR: GenerateSelectorPayload,
        TaskName.EXTRACT_LINKS: ExtractLinksPayload,
        TaskName.PROCESS_PROJECT_ENTRIES: ProcessProjectEntriesPayload,
        TaskName.GENERATE_SEARCH_PARAMS: GenerateSearchParamsPayload,
    }
    if db_row.get("payload") is not None:
        payload_model: BaseModel = payload_map[task_name]
        db_row["payload"] = payload_model.model_validate(db_row["payload"])

    result_map = {
        TaskName.GENERATE_SELECTOR: GenerateSelectorResult,
        TaskName.EXTRACT_LINKS: ExtractLinksResult,
        TaskName.PROCESS_PROJECT_ENTRIES: ProcessProjectEntriesResult,
        TaskName.GENERATE_SEARCH_PARAMS: GenerateSearchParamsResult,
    }
    if db_row.get("result") is not None:
        result_model: BaseModel = result_map[task_name]
        db_row["result"] = result_model.model_validate(db_row["result"])

    return BackgroundJob(**db_row)


async def create_background_job(job: CreateBackgroundJob) -> BackgroundJob:
    """Create a new background job and return it."""
    job_id = uuid4()
    query = """
        INSERT INTO "BackgroundJob" (id, task_name, project_id, payload)
        VALUES (%s, %s, %s, %s)
    """
    params = (
        job_id,
        job.task_name.value,
        job.project_id,
        job.payload.model_dump_json() if job.payload else None,
    )
    await execute_query(query, params)
    new_job = await get_background_job(job_id)
    if not new_job:
        raise Exception("Failed to retrieve newly created job")
    return new_job


async def get_background_job(job_id: UUID) -> BackgroundJob | None:
    """Retrieve a background job by its ID."""
    query = 'SELECT * FROM "BackgroundJob" WHERE id = %s'
    result = await fetchrow_query(query, (job_id,))
    return _deserialize_job(result) if result else None


async def list_background_jobs_paginated(
    limit: int = 50, offset: int = 0
) -> PaginatedResponse[BackgroundJob]:
    """List all background jobs with pagination, newest first."""
    query = 'SELECT * FROM "BackgroundJob" ORDER BY created_at DESC LIMIT %s OFFSET %s'
    results = await fetch_query(query, (limit, offset))
    jobs = [_deserialize_job(row) for row in results] if results else []
    total_items = await count_background_jobs()
    current_page = offset // limit + 1

    return PaginatedResponse(
        data=jobs,
        meta=PaginationMeta(
            current_page=current_page,
            per_page=limit,
            total_items=total_items,
        ),
    )


async def count_background_jobs() -> int:
    """Count all background jobs."""
    query = 'SELECT COUNT(*) FROM "BackgroundJob"'
    result = await fetchrow_query(query)
    return result["count"] if result else 0


async def count_in_progress_background_jobs_by_task_name(task_name: TaskName) -> int:
    """Count the number of 'in_progress' jobs for a specific task name."""
    query = """
        SELECT COUNT(*)
        FROM "BackgroundJob"
        WHERE task_name = %s AND status = 'in_progress'
    """
    result = await fetchrow_query(query, (task_name.value,))
    return result["count"] if result else 0


async def get_and_lock_pending_background_job() -> BackgroundJob | None:
    """
    Atomically retrieve the oldest pending job and set its status to 'in_progress'.
    This uses 'SELECT ... FOR UPDATE SKIP LOCKED' to prevent race conditions.
    """
    # This query is specific to PostgreSQL.
    query = """
        WITH oldest_pending AS (
            SELECT id
            FROM "BackgroundJob"
            WHERE status = 'pending'
            ORDER BY created_at
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        UPDATE "BackgroundJob"
        SET status = 'in_progress', updated_at = NOW()
        WHERE id = (SELECT id FROM oldest_pending)
        RETURNING *;
    """
    result = await fetchrow_query(query)
    return _deserialize_job(result) if result else None


async def update_background_job(
    job_id: UUID, job_update: UpdateBackgroundJob
) -> BackgroundJob | None:
    """Update a background job's state."""
    update_data = job_update.model_dump(exclude_unset=True)
    if not update_data:
        return await get_background_job(job_id)

    set_clause_parts = []
    params: List[Any] = []
    for key, value in update_data.items():
        set_clause_parts.append(f'"{key}" = %s')
        if key == "result" and value is not None:
            params.append(json.dumps(value))
        else:
            params.append(value)

    if not set_clause_parts:
        return await get_background_job(job_id)

    params.append(job_id)
    set_clause = ", ".join(set_clause_parts)
    query = f'UPDATE "BackgroundJob" SET {set_clause}, updated_at = NOW() WHERE id = %s'

    await execute_query(query, tuple(params))
    return await get_background_job(job_id)


async def delete_background_job(job_id: UUID) -> None:
    """Delete a background job from the database."""
    query = 'DELETE FROM "BackgroundJob" WHERE id = %s'
    await execute_query(query, (job_id,))

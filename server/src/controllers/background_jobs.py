from uuid import UUID
from litestar import Controller, get, post
from litestar.exceptions import NotFoundException, HTTPException
from litestar.params import Body
from pydantic import BaseModel, Field
from typing import Optional, List

from logging_config import get_logger
from db.background_jobs import (
    BackgroundJob,
    CreateBackgroundJob,
    ConfirmLinksPayload,
    GenerateSearchParamsPayload,
    DiscoverAndCrawlSourcesPayload,
    ProcessProjectEntriesPayload,
    UpdateBackgroundJob,
    TaskName,
    JobStatus,
    create_background_job as db_create_background_job,
    get_background_job as db_get_background_job,
    get_latest_job_by_task_name as db_get_latest_job_by_task_name,
    list_background_jobs_paginated as db_list_background_jobs_paginated,
    update_background_job as db_update_background_job,
)
from db.common import PaginatedResponse, SingleResponse
from db.projects import get_project as db_get_project
from db.connection import get_db_connection
from db.source_hierarchy import (
    get_source_hierarchy_for_project as db_get_source_hierarchy_for_project,
)

logger = get_logger(__name__)


class CreateJobForProjectPayload(BaseModel):
    project_id: str


class CreateJobForSourcePayload(BaseModel):
    project_id: str
    source_ids: list[UUID] = Field(..., min_length=1)


class ConfirmLinksJobPayload(BaseModel):
    project_id: str
    urls: list[str]


class ProcessEntriesJobPayload(BaseModel):
    project_id: str
    link_ids: Optional[List[UUID]] = None


class BackgroundJobController(Controller):
    path = "/jobs"

    @get("/")
    async def list_jobs(
        self, limit: int = 50, offset: int = 0
    ) -> PaginatedResponse[BackgroundJob]:
        """List all background jobs with pagination."""
        logger.debug("Listing all background jobs")
        return await db_list_background_jobs_paginated(limit, offset)

    @get("/{job_id:uuid}")
    async def get_job(self, job_id: UUID) -> SingleResponse[BackgroundJob]:
        """Retrieve a single background job by its ID."""
        logger.debug(f"Retrieving job {job_id}")
        job = await db_get_background_job(job_id)
        if not job:
            raise NotFoundException(f"Job '{job_id}' not found.")
        return SingleResponse(data=job)

    @get("/latest")
    async def get_latest_job(
        self, project_id: str, task_name: TaskName
    ) -> SingleResponse[BackgroundJob]:
        """Retrieve the latest job for a project by task name."""
        logger.debug(
            f"Retrieving latest job for project {project_id} with task {task_name.value}"
        )
        job = await db_get_latest_job_by_task_name(project_id, task_name)
        if not job:
            raise NotFoundException(
                f"No job with task name '{task_name.value}' found for project '{project_id}'."
            )
        return SingleResponse(data=job)

    @post("/{job_id:uuid}/cancel")
    async def cancel_job(self, job_id: UUID) -> SingleResponse[BackgroundJob]:
        """Request cancellation of a running or pending job."""
        async with (await get_db_connection()).transaction() as tx:
            logger.debug(f"Cancelling job {job_id}")
            job = await db_get_background_job(job_id, tx=tx)
            if not job:
                raise NotFoundException(f"Job '{job_id}' not found.")

            if job.status in [
                JobStatus.completed,
                JobStatus.failed,
                JobStatus.canceled,
            ]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Job '{job_id}' is already in a terminal state ({job.status}).",
                )

            if job.status == JobStatus.in_progress:
                updated_job = await db_update_background_job(
                    job_id, UpdateBackgroundJob(status=JobStatus.cancelling), tx=tx
                )
            else:  # pending
                updated_job = await db_update_background_job(
                    job_id, UpdateBackgroundJob(status=JobStatus.canceled), tx=tx
                )

            if not updated_job:
                raise NotFoundException(f"Job '{job_id}' not found after update.")

            return SingleResponse(data=updated_job)

    @post("/discover-and-crawl")
    async def create_discover_and_crawl_job(
        self, data: CreateJobForSourcePayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to discover sub-sources and crawl for content links."""
        async with (await get_db_connection()).transaction() as tx:
            hierarchy = await db_get_source_hierarchy_for_project(
                data.project_id, tx=tx
            )
            child_to_parent_map = {
                rel.child_source_id: rel.parent_source_id for rel in hierarchy
            }
            selected_ids_set = set(data.source_ids)

            for source_id in data.source_ids:
                current_id = source_id
                while current_id in child_to_parent_map:
                    parent_id = child_to_parent_map[current_id]
                    if parent_id in selected_ids_set:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid selection: Source {source_id} is a descendant of another selected source {parent_id}. Please submit only top-level sources for processing.",
                        )
                    current_id = parent_id

            logger.debug(
                f"Creating discover_and_crawl_sources job for sources {data.source_ids}"
            )
            job = await db_create_background_job(
                CreateBackgroundJob(
                    task_name=TaskName.DISCOVER_AND_CRAWL_SOURCES,
                    project_id=data.project_id,
                    payload=DiscoverAndCrawlSourcesPayload(source_ids=data.source_ids),
                ),
                tx=tx,
            )
            return SingleResponse(data=job)

    @post("/confirm-links")
    async def create_confirm_links_job(
        self, data: ConfirmLinksJobPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to confirm and save links for a project."""
        async with (await get_db_connection()).transaction() as tx:
            logger.debug(f"Creating confirm_links job for project {data.project_id}")
            project = await db_get_project(data.project_id, tx=tx)
            if not project:
                raise NotFoundException(f"Project '{data.project_id}' not found.")

            job = await db_create_background_job(
                CreateBackgroundJob(
                    task_name=TaskName.CONFIRM_LINKS,
                    project_id=data.project_id,
                    payload=ConfirmLinksPayload(urls=data.urls),
                ),
                tx=tx,
            )
            return SingleResponse(data=job)

    @post("/process-project-entries")
    async def create_process_project_entries_job(
        self, data: ProcessEntriesJobPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to process all pending links for a project."""
        async with (await get_db_connection()).transaction() as tx:
            logger.debug(
                f"Creating process_project_entries job for project {data.project_id}"
            )
            project = await db_get_project(data.project_id, tx=tx)
            if not project:
                raise NotFoundException(f"Project '{data.project_id}' not found.")

            job = await db_create_background_job(
                CreateBackgroundJob(
                    task_name=TaskName.PROCESS_PROJECT_ENTRIES,
                    project_id=data.project_id,
                    payload=ProcessProjectEntriesPayload(link_ids=data.link_ids),
                ),
                tx=tx,
            )
            return SingleResponse(data=job)

    @post("/generate-search-params")
    async def create_generate_search_params_job(
        self, data: CreateJobForProjectPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to generate search parameters for a project."""
        async with (await get_db_connection()).transaction() as tx:
            logger.debug(
                f"Creating generate_search_params job for project {data.project_id}"
            )
            project = await db_get_project(data.project_id, tx=tx)
            if not project:
                raise NotFoundException(f"Project '{data.project_id}' not found.")

            job = await db_create_background_job(
                CreateBackgroundJob(
                    task_name=TaskName.GENERATE_SEARCH_PARAMS,
                    project_id=data.project_id,
                    payload=GenerateSearchParamsPayload(),
                ),
                tx=tx,
            )
            return SingleResponse(data=job)

    @post("/rescan-links")
    async def create_rescan_links_job(
        self, data: CreateJobForSourcePayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to rescan links for specific sources."""
        logger.debug(f"Creating rescan_links job for sources {data.source_ids}")
        # Basic validation to ensure sources exist and have selectors can be added here
        job = await db_create_background_job(
            CreateBackgroundJob(
                task_name=TaskName.RESCAN_LINKS,
                project_id=data.project_id,
                payload=DiscoverAndCrawlSourcesPayload(source_ids=data.source_ids),
            )
        )
        return SingleResponse(data=job)

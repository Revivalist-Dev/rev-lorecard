from uuid import UUID
from litestar import Controller, get, post
from litestar.exceptions import NotFoundException, HTTPException
from litestar.params import Body
from pydantic import BaseModel

from logging_config import get_logger
from db.background_jobs import (
    BackgroundJob,
    CreateBackgroundJob,
    ExtractLinksPayload,
    GenerateSearchParamsPayload,
    GenerateSelectorPayload,
    ProcessProjectEntriesPayload,
    UpdateBackgroundJob,
    TaskName,
    JobStatus,
    create_background_job as db_create_background_job,
    get_background_job as db_get_background_job,
    list_background_jobs_paginated as db_list_background_jobs_paginated,
    update_background_job as db_update_background_job,
)
from db.common import PaginatedResponse, SingleResponse
from db.projects import get_project as db_get_project

logger = get_logger(__name__)


class CreateJobForProjectPayload(BaseModel):
    project_id: str


class ExtractLinksJobPayload(BaseModel):
    project_id: str
    urls: list[str]


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

    @post("/{job_id:uuid}/cancel")
    async def cancel_job(self, job_id: UUID) -> SingleResponse[BackgroundJob]:
        """Request cancellation of a running or pending job."""
        logger.debug(f"Cancelling job {job_id}")
        job = await db_get_background_job(job_id)
        if not job:
            raise NotFoundException(f"Job '{job_id}' not found.")

        if job.status in [JobStatus.completed, JobStatus.failed, JobStatus.canceled]:
            raise HTTPException(
                status_code=400,
                detail=f"Job '{job_id}' is already in a terminal state ({job.status}).",
            )

        if job.status == JobStatus.in_progress:
            updated_job = await db_update_background_job(
                job_id, UpdateBackgroundJob(status=JobStatus.cancelling)
            )
        else:  # pending
            updated_job = await db_update_background_job(
                job_id, UpdateBackgroundJob(status=JobStatus.canceled)
            )

        if not updated_job:
            raise NotFoundException(f"Job '{job_id}' not found after update.")

        return SingleResponse(data=updated_job)

    @post("/generate-selector")
    async def create_generate_selector_job(
        self, data: CreateJobForProjectPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to generate the CSS selector for a project."""
        logger.debug(f"Creating generate_selector job for project {data.project_id}")
        project = await db_get_project(data.project_id)
        if not project:
            raise NotFoundException(f"Project '{data.project_id}' not found.")

        job = await db_create_background_job(
            CreateBackgroundJob(
                task_name=TaskName.GENERATE_SELECTOR,
                project_id=data.project_id,
                payload=GenerateSelectorPayload(),
            )
        )
        return SingleResponse(data=job)

    @post("/extract-links")
    async def create_extract_links_job(
        self, data: ExtractLinksJobPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to extract links for a project."""
        logger.debug(f"Creating extract_links job for project {data.project_id}")
        project = await db_get_project(data.project_id)
        if not project:
            raise NotFoundException(f"Project '{data.project_id}' not found.")

        job = await db_create_background_job(
            CreateBackgroundJob(
                task_name=TaskName.EXTRACT_LINKS,
                project_id=data.project_id,
                payload=ExtractLinksPayload(urls=data.urls),
            )
        )
        return SingleResponse(data=job)

    @post("/process-project-entries")
    async def create_process_project_entries_job(
        self, data: CreateJobForProjectPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to process all pending links for a project."""
        logger.debug(
            f"Creating process_project_entries job for project {data.project_id}"
        )
        project = await db_get_project(data.project_id)
        if not project:
            raise NotFoundException(f"Project '{data.project_id}' not found.")

        job = await db_create_background_job(
            CreateBackgroundJob(
                task_name=TaskName.PROCESS_PROJECT_ENTRIES,
                project_id=data.project_id,
                payload=ProcessProjectEntriesPayload(),
            )
        )
        return SingleResponse(data=job)

    @post("/generate-search-params")
    async def create_generate_search_params_job(
        self, data: CreateJobForProjectPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to generate search parameters for a project."""
        logger.debug(
            f"Creating generate_search_params job for project {data.project_id}"
        )
        project = await db_get_project(data.project_id)
        if not project:
            raise NotFoundException(f"Project '{data.project_id}' not found.")

        job = await db_create_background_job(
            CreateBackgroundJob(
                task_name=TaskName.GENERATE_SEARCH_PARAMS,
                project_id=data.project_id,
                payload=GenerateSearchParamsPayload(),
            )
        )
        return SingleResponse(data=job)

    @post("/rescan-links")
    async def create_rescan_links_job(
        self, data: CreateJobForProjectPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Create a job to rescan links using existing selectors for a project."""
        logger.debug(f"Creating rescan_links job for project {data.project_id}")
        project = await db_get_project(data.project_id)
        if not project:
            raise NotFoundException(f"Project '{data.project_id}' not found.")

        if not project.link_extraction_selector:
            raise HTTPException(
                status_code=400,
                detail="Project has no selectors to use for rescanning. Please generate them first.",
            )

        job = await db_create_background_job(
            CreateBackgroundJob(
                task_name=TaskName.RESCAN_LINKS,
                project_id=data.project_id,
                payload=GenerateSelectorPayload(),
            )
        )
        return SingleResponse(data=job)

from uuid import UUID
from litestar import Controller, get, post, patch, delete
from litestar.exceptions import NotFoundException, HTTPException
from litestar.params import Body
from pydantic import BaseModel
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from db.background_jobs import create_background_job, TaskName, BackgroundJob
from schemas import AISourceEditJobPayload
from soupsieve.util import SelectorSyntaxError
import httpx

from db.sources import (
    ProjectSource,
    CreateProjectSource,
    UpdateProjectSource,
    SourceContentVersion,
    create_project_source,
    delete_project_sources_bulk,
    list_sources_by_project,
    update_project_source,
    delete_project_source,
    get_project_source as db_get_project_source,
    list_source_content_versions,
    get_source_content_version,
    delete_source_content_version,
    clear_source_content_history,
)
from db.source_hierarchy import (
    ProjectSourceHierarchy,
    get_source_hierarchy_for_project,
)
from db.common import SingleResponse
from db.projects import get_project as db_get_project
from services.scraper import Scraper
from logging_config import get_logger

logger = get_logger(__name__)


class BulkDeleteSourcesPayload(BaseModel):
    source_ids: list[UUID]


class TestSelectorsPayload(BaseModel):
    url: str
    content_selectors: List[str]
    pagination_selector: Optional[str] = None


class TestSelectorsResult(BaseModel):
    content_links: List[str]
    pagination_link: Optional[str] = None
    error: Optional[str] = None
    link_count: int


class SourceController(Controller):
    path = "/projects/{project_id:str}/sources"

    @get("/")
    async def list_project_sources(self, project_id: str) -> list[ProjectSource]:
        logger.debug(f"Listing sources for project {project_id}")
        return await list_sources_by_project(project_id)

    @get("/hierarchy")
    async def get_project_source_hierarchy(
        self, project_id: str
    ) -> list[ProjectSourceHierarchy]:
        logger.debug(f"Getting source hierarchy for project {project_id}")
        return await get_source_hierarchy_for_project(project_id)

    @post("/")
    async def add_project_source(
        self, project_id: str, data: dict = Body()
    ) -> SingleResponse[ProjectSource]:
        logger.debug(f"Adding source to project {project_id}")
        source_data = CreateProjectSource(project_id=project_id, **data)
        source = await create_project_source(source_data)
        return SingleResponse(data=source)

    @get("/{source_id:uuid}")
    async def get_source_details(
        self, project_id: str, source_id: UUID
    ) -> SingleResponse[ProjectSource]:
        """Gets the full details of a single source, including its raw_content."""
        logger.debug(f"Getting details for source {source_id}")
        source = await db_get_project_source(source_id)
        if not source or source.project_id != project_id:
            raise NotFoundException(
                f"Source '{source_id}' not found in project '{project_id}'."
            )
        return SingleResponse(data=source)

    @post("/test-selectors")
    async def test_project_source_selectors(
        self, data: TestSelectorsPayload = Body()
    ) -> TestSelectorsResult:
        """Tests CSS selectors against a URL and returns the extracted links."""
        logger.debug(f"Testing selectors for URL: {data.url}")
        scraper = Scraper()
        content_links = set()
        pagination_link = None
        error_message = None

        try:
            html = await scraper.get_content(data.url, clean=True, pretty=True)
            soup = BeautifulSoup(html, "html.parser")

            # Test content selectors
            for selector in data.content_selectors:
                if not selector:
                    continue
                try:
                    for link_tag in soup.select(selector):
                        if href := link_tag.get("href"):
                            absolute_url = urljoin(data.url, href)  # pyright: ignore[reportArgumentType]
                            content_links.add(absolute_url)
                except SelectorSyntaxError as e:
                    raise ValueError(f"Invalid content selector '{selector}': {e}")

            # Test pagination selector
            if data.pagination_selector:
                try:
                    next_page_tag = soup.select_one(data.pagination_selector)
                    if next_page_tag and next_page_tag.get("href"):
                        pagination_link = urljoin(data.url, next_page_tag.get("href"))  # pyright: ignore[reportArgumentType]
                except SelectorSyntaxError as e:
                    raise ValueError(
                        f"Invalid pagination selector '{data.pagination_selector}': {e}"
                    )

        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            error_message = f"Failed to fetch URL: {e}"
        except ValueError as e:
            error_message = str(e)
        except Exception as e:
            logger.error(f"Unexpected error during selector test: {e}", exc_info=True)
            error_message = "An unexpected server error occurred."

        if error_message:
            raise HTTPException(status_code=400, detail=error_message)

        return TestSelectorsResult(
            content_links=sorted(list(content_links)),
            pagination_link=pagination_link,
            link_count=len(content_links),
        )

    @post("/ai-edit")
    async def ai_edit_source_content(
        self, project_id: str, data: AISourceEditJobPayload = Body()
    ) -> SingleResponse[BackgroundJob]:
        """Triggers a background job to use AI to edit the raw content of a source."""
        logger.info(
            f"Triggering AI edit job for source {data.source_id} in project {project_id}"
        )

        project = await db_get_project(project_id)
        if not project:
            raise NotFoundException(f"Project '{project_id}' not found.")

        if not project.ai_provider_id or not project.ai_model_id:
            raise HTTPException(
                status_code=400,
                detail="AI provider and model must be configured for this project.",
            )

        job = await create_background_job(
            project_id=project_id,
            task_name=TaskName.AI_EDIT_SOURCE_CONTENT,
            payload=data,
        )
        return SingleResponse(data=job)

    @get("/{source_id:uuid}/versions")
    async def list_source_versions(
        self, project_id: str, source_id: UUID
    ) -> List[SourceContentVersion]:
        """Lists all historical content versions for a source."""
        source = await db_get_project_source(source_id)
        if not source or source.project_id != project_id:
            raise NotFoundException(
                f"Source '{source_id}' not found in project '{project_id}'."
            )
        
        # SourceContentVersion is defined in db.sources, need to import it
        from db.sources import SourceContentVersion
        
        return await list_source_content_versions(source_id)

    @post("/{source_id:uuid}/versions/{version_id:uuid}/restore")
    async def restore_source_version(
        self, project_id: str, source_id: UUID, version_id: UUID
    ) -> SingleResponse[ProjectSource]:
        """Restores a historical content version to the current source content."""
        version = await get_source_content_version(version_id)
        if not version or version.project_id != project_id or version.source_id != source_id:
            raise NotFoundException(
                f"Version '{version_id}' not found for source '{source_id}' in project '{project_id}'."
            )

        # The update_project_source function handles creating a backup of the current content
        # before applying the new content (the restored version).
        updated_source = await update_project_source(
            source_id,
            UpdateProjectSource(
                raw_content=version.raw_content,
                # We don't update content_type here, relying on update_project_source's default logic
            ),
        )

        if not updated_source:
            raise HTTPException(status_code=500, detail="Failed to restore source content.")

        return SingleResponse(data=updated_source)

    @delete("/{source_id:uuid}/versions/{version_id:uuid}")
    async def delete_source_version(
        self, project_id: str, source_id: UUID, version_id: UUID
    ) -> None:
        """Deletes a specific historical content version."""
        version = await get_source_content_version(version_id)
        if not version or version.project_id != project_id or version.source_id != source_id:
            raise NotFoundException(
                f"Version '{version_id}' not found for source '{source_id}' in project '{project_id}'."
            )
        
        # Check if this is the latest version (which should be protected)
        versions = await list_source_content_versions(source_id)
        if versions and versions[0].id == version_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the latest version of the source content.",
            )

        await delete_source_content_version(version_id)

    @post("/{source_id:uuid}/versions/clear-history")
    async def clear_source_history(
        self, project_id: str, source_id: UUID
    ) -> None:
        """Deletes all historical content versions for a source, keeping only the latest."""
        source = await db_get_project_source(source_id)
        if not source or source.project_id != project_id:
            raise NotFoundException(
                f"Source '{source_id}' not found in project '{project_id}'."
            )
        
        await clear_source_content_history(source_id)

    @patch("/{source_id:uuid}")
    async def update_source(
        self, project_id: str, source_id: UUID, data: UpdateProjectSource = Body()
    ) -> SingleResponse[ProjectSource]:
        logger.debug(f"Updating source {source_id} for project {project_id}")
        
        # Check if source exists and belongs to the project before updating
        existing_source = await db_get_project_source(source_id)
        if not existing_source or existing_source.project_id != project_id:
            raise NotFoundException(
                f"Source '{source_id}' not found in project '{project_id}'."
            )

        source = await update_project_source(source_id, data)
        if not source:
            # This should ideally not happen if existing_source was found, but for safety:
            raise NotFoundException(f"Source '{source_id}' not found after update attempt.")
        return SingleResponse(data=source)

    @delete("/{source_id:uuid}")
    async def delete_source(self, source_id: UUID) -> None:
        logger.debug(f"Deleting source {source_id}")
        await delete_project_source(source_id)

    @post("/delete-bulk")
    async def delete_sources_bulk(
        self, project_id: str, data: BulkDeleteSourcesPayload = Body()
    ) -> None:
        """Deletes multiple sources for a project in a single request."""
        logger.debug(
            f"Bulk deleting {len(data.source_ids)} sources for project {project_id}"
        )
        await delete_project_sources_bulk(project_id, data.source_ids)

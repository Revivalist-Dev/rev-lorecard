from uuid import UUID
from litestar import Controller, get, post, patch, delete
from litestar.exceptions import NotFoundException, HTTPException
from litestar.params import Body
from pydantic import BaseModel
from typing import List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from soupsieve.util import SelectorSyntaxError
import httpx

from db.sources import (
    ProjectSource,
    CreateProjectSource,
    UpdateProjectSource,
    create_project_source,
    delete_project_sources_bulk,
    list_sources_by_project,
    update_project_source,
    delete_project_source,
)
from db.source_hierarchy import (
    ProjectSourceHierarchy,
    get_source_hierarchy_for_project,
)
from db.common import SingleResponse
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

    @patch("/{source_id:uuid}")
    async def update_source(
        self, source_id: UUID, data: UpdateProjectSource = Body()
    ) -> SingleResponse[ProjectSource]:
        logger.debug(f"Updating source {source_id}")
        source = await update_project_source(source_id, data)
        if not source:
            raise NotFoundException(f"Source '{source_id}' not found.")
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

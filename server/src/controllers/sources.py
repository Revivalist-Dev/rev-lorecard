from uuid import UUID
from litestar import Controller, get, post, patch, delete
from litestar.exceptions import NotFoundException
from litestar.params import Body

from db.sources import (
    ProjectSource,
    CreateProjectSource,
    UpdateProjectSource,
    create_project_source,
    list_sources_by_project,
    update_project_source,
    delete_project_source,
)
from db.common import SingleResponse
from logging_config import get_logger

logger = get_logger(__name__)


class SourceController(Controller):
    path = "/projects/{project_id:str}/sources"

    @get("/")
    async def list_project_sources(self, project_id: str) -> list[ProjectSource]:
        logger.debug(f"Listing sources for project {project_id}")
        return await list_sources_by_project(project_id)

    @post("/")
    async def add_project_source(
        self, project_id: str, data: dict = Body()
    ) -> SingleResponse[ProjectSource]:
        logger.debug(f"Adding source to project {project_id}")
        source_data = CreateProjectSource(project_id=project_id, **data)
        source = await create_project_source(source_data)
        return SingleResponse(data=source)

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

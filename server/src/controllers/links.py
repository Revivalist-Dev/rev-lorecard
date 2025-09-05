from uuid import UUID
from litestar import Controller, post
from litestar.params import Body
from pydantic import BaseModel, Field

from db.links import delete_links_bulk as db_delete_links_bulk
from logging_config import get_logger

logger = get_logger(__name__)


class BulkDeleteLinksPayload(BaseModel):
    link_ids: list[UUID] = Field(..., min_length=1)


class LinksController(Controller):
    path = "/projects/{project_id:str}/links"

    @post("/delete-bulk")
    async def delete_links_bulk(
        self, project_id: str, data: BulkDeleteLinksPayload = Body()
    ) -> None:
        """Deletes multiple links for a project in a single request."""
        logger.debug(
            f"Bulk deleting {len(data.link_ids)} links for project {project_id}"
        )
        await db_delete_links_bulk(project_id, data.link_ids)

from litestar import Controller, get
from litestar.exceptions import NotFoundException

from db.analytics import ProjectAnalytics, get_project_analytics
from db.common import SingleResponse
from db.projects import get_project as db_get_project
from logging_config import get_logger

logger = get_logger(__name__)


class AnalyticsController(Controller):
    path = "/analytics"

    @get("/projects/{project_id:str}")
    async def get_analytics_for_project(
        self, project_id: str
    ) -> SingleResponse[ProjectAnalytics]:
        """Get aggregated cost and usage statistics for a project."""
        logger.debug(f"Getting analytics for project {project_id}")
        project = await db_get_project(project_id)
        if not project:
            raise NotFoundException(f"Project '{project_id}' not found.")

        analytics = await get_project_analytics(project_id)
        if not analytics:
            raise NotFoundException(f"Analytics for project '{project_id}' not found.")

        return SingleResponse(data=analytics)

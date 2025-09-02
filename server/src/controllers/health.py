from litestar import Controller, get
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from pydantic import BaseModel

from db.connection import get_db_connection
from logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(BaseModel):
    status: str
    database: str


class HealthController(Controller):
    path = "/health"

    @get(path="/")
    async def get_health_status(self) -> Response[HealthStatus]:
        """
        Performs a health check of the application and its database connection.
        """
        db_status = "ok"
        try:
            db = await get_db_connection()
            # Perform a simple, non-blocking query to check the connection
            await db.fetch_one("SELECT 1")
        except Exception as e:
            logger.error(f"Database health check failed: {e}", exc_info=True)
            db_status = "error"

        if db_status == "ok":
            return Response(
                HealthStatus(status="ok", database="ok"), status_code=HTTP_200_OK
            )
        else:
            return Response(
                HealthStatus(status="error", database="error"),
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )

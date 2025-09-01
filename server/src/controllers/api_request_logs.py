from litestar import Controller, get
from litestar.exceptions import NotFoundException
from uuid import UUID
from logging_config import get_logger

from db.api_request_logs import (
    ApiRequestLog,
    get_api_request_log,
)

logger = get_logger(__name__)


class ApiRequestLogController(Controller):
    path = "/logs"

    @get("/{log_id:uuid}")
    async def get_api_request_log(self, log_id: UUID) -> ApiRequestLog:
        """Retrieve a single API request log by its ID."""
        logger.debug(f"Retrieving API request log {log_id}")
        log = await get_api_request_log(log_id)
        if not log:
            raise NotFoundException(f"ApiRequestLog '{log_id}' not found.")
        return log

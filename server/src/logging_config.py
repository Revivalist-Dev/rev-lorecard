import logging
import os
import json
from rich.logging import RichHandler


class JsonFormatter(logging.Formatter):
    """
    Formats log records as a JSON string.
    """

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging():
    is_production = os.getenv("APP_ENV", "development").lower() == "production"

    if is_production:
        # Configure for production: JSON output to stdout
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logging.basicConfig(level=logging.INFO, handlers=[handler])
        # Suppress uvicorn's default access logger to avoid duplicate logs
        logging.getLogger("uvicorn.access").handlers = []
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)],
        )
        # Set DB-related logs to DEBUG for debugging migrations
        logging.getLogger("db").setLevel(logging.DEBUG)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


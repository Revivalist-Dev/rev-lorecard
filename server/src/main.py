import asyncio
import sys
from dotenv import load_dotenv
from logging_config import get_logger, setup_logging

import uvicorn
from litestar import Litestar
from litestar.router import Router
from litestar.exceptions import ValidationException
from litestar.config.cors import CORSConfig
import threading

from worker import run_worker
from controllers.api_request_logs import ApiRequestLogController
from controllers.providers import ProviderController
from controllers.sse import SSEController
from controllers.projects import ProjectController
from controllers.lorebook_entries import LorebookEntryController
from controllers.background_jobs import BackgroundJobController
from controllers.analytics import AnalyticsController
from controllers.global_templates import GlobalTemplateController
from exceptions import (
    generic_exception_handler,
    validation_exception_handler,
    value_error_exception_handler,
)
from db.global_templates import create_global_template, get_global_template
from db.global_templates import CreateGlobalTemplate
import default_templates

import providers.openrouter  # noqa: F401

logger = get_logger(__name__)

cors_config = CORSConfig(
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"]
)


async def create_default_templates():
    """Create default global templates if they don't exist."""
    templates_to_create = [
        CreateGlobalTemplate(
            id="selector-prompt",
            name="selector_prompt",
            content=default_templates.selector_prompt,
        ),
        CreateGlobalTemplate(
            id="search-params-prompt",
            name="search_params_prompt",
            content=default_templates.search_params_prompt,
        ),
        CreateGlobalTemplate(
            id="entry-creation-prompt",
            name="entry_creation_prompt",
            content=default_templates.entry_creation_prompt,
        ),
        CreateGlobalTemplate(
            id="lorebook-definition",
            name="lorebook_definition",
            content=default_templates.lorebook_definition,
        ),
    ]
    for template in templates_to_create:
        existing_template = await get_global_template(template.id)
        if not existing_template:
            await create_global_template(template)
            logger.info(f"Created default template: {template.name}")


def create_app():
    api_router = Router(
        path="/api",
        exception_handlers={
            Exception: generic_exception_handler,
            ValidationException: validation_exception_handler,
            ValueError: value_error_exception_handler,
        },
        route_handlers=[
            ApiRequestLogController,
            ProviderController,
            SSEController,
            ProjectController,
            LorebookEntryController,
            BackgroundJobController,
            AnalyticsController,
            GlobalTemplateController,
        ],
    )

    return Litestar(
        cors_config=cors_config,
        exception_handlers={
            Exception: generic_exception_handler,
            ValidationException: validation_exception_handler,
            ValueError: value_error_exception_handler,
        },
        route_handlers=[api_router],
        on_startup=[create_default_templates],
    )


app = create_app()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    logger.info("Starting worker thread")

    def run_worker_in_loop():
        asyncio.run(run_worker())

    worker_thread = threading.Thread(target=run_worker_in_loop, daemon=True)
    worker_thread.start()

    logger.info("Starting API server")
    uvicorn.run(app, host="0.0.0.0", port=3000)

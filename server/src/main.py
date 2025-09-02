import asyncio
from pathlib import Path
import sys
from dotenv import load_dotenv
from db.background_jobs import reset_in_progress_jobs_to_pending
from logging_config import get_logger, setup_logging
import os

import uvicorn
from litestar import Litestar, asgi, get
from litestar.router import Router
from litestar.exceptions import ValidationException
from litestar.config.cors import CORSConfig
from litestar.static_files import StaticFiles
from litestar.types import Receive, Scope, Send
from litestar.file_system import BaseLocalFileSystem
from litestar.response.file import ASGIFileResponse
import threading
from pydantic import BaseModel

from worker import run_worker
from controllers.api_request_logs import ApiRequestLogController
from controllers.providers import ProviderController
from controllers.sse import SSEController
from controllers.projects import ProjectController
from controllers.lorebook_entries import LorebookEntryController
from controllers.background_jobs import (
    BackgroundJobController,
)
from controllers.analytics import AnalyticsController
from controllers.global_templates import GlobalTemplateController
from exceptions import (
    generic_exception_handler,
    validation_exception_handler,
    value_error_exception_handler,
)
from db.connection import init_database
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


async def recover_stale_jobs():
    """Resets 'in_progress' jobs to 'pending' on startup."""
    logger.info("Checking for stale jobs to recover...")
    await reset_in_progress_jobs_to_pending()


CLIENT_BUILD_DIR = Path(__file__).parent.parent.parent / "client" / "dist"
assets_app = StaticFiles(
    is_html_mode=False,
    directories=[CLIENT_BUILD_DIR / "assets"],
    file_system=BaseLocalFileSystem(),
)


@asgi(path="/assets", is_static=True)
async def serve_assets(scope: Scope, receive: Receive, send: Send) -> None:
    """Handles serving static assets from the /assets directory."""
    await assets_app(scope, receive, send)


@get(path=["/", "/{path:path}"], sync_to_thread=False)
async def spa_fallback(path: str | None = None) -> ASGIFileResponse:
    """
    Serves the index.html file for all non-API and non-asset routes.
    This is the catch-all for the Single-Page Application.
    """
    return ASGIFileResponse(
        file_path=CLIENT_BUILD_DIR / "index.html",
        media_type="text/html",
        filename="index.html",
        content_disposition_type="inline",
    )


class AppInfo(BaseModel):
    version: str


@get(path="/info", sync_to_thread=False)
async def get_app_info() -> AppInfo:
    """Returns basic application information, like the version."""
    return AppInfo(version=os.getenv("APP_VERSION", "development"))


def create_app():
    api_router = Router(
        path="/api",
        exception_handlers={
            Exception: generic_exception_handler,
            ValidationException: validation_exception_handler,
            ValueError: value_error_exception_handler,
        },
        route_handlers=[
            get_app_info,
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
        route_handlers=[
            api_router,
            serve_assets,
            spa_fallback,
        ],
        on_startup=[create_default_templates, recover_stale_jobs],
        static_files_config=None,
    )


app = create_app()


async def main():
    """Main function to orchestrate application startup."""
    load_dotenv()
    setup_logging()

    logger.info("Initializing database...")
    await init_database()
    logger.info("Database initialization complete.")

    logger.info("Starting worker thread...")
    worker_thread = threading.Thread(
        target=lambda: asyncio.run(run_worker()), daemon=True
    )
    worker_thread.start()

    port = int(os.getenv("PORT", 3000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_config=None)
    server = uvicorn.Server(config)

    logger.info(f"Starting API server on http://0.0.0.0:{port}")
    await server.serve()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

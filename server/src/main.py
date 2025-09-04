import asyncio
from pathlib import Path
import sys
from typing import Literal, Optional
from dotenv import load_dotenv
import httpx
from db.background_jobs import reset_in_progress_jobs_to_pending
from db.common import CreateGlobalTemplate
from db.links import reset_processing_links_to_pending
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
from controllers.sources import SourceController
from controllers.lorebook_entries import LorebookEntryController
from controllers.background_jobs import (
    BackgroundJobController,
)
from controllers.analytics import AnalyticsController
from controllers.global_templates import GlobalTemplateController
from controllers.health import HealthController
from exceptions import (
    generic_exception_handler,
    validation_exception_handler,
    value_error_exception_handler,
)
from db.connection import close_database, init_database
from db.global_templates import create_global_template, get_global_template
import default_templates

import providers.openrouter  # noqa: F401
import providers.gemini  # noqa: F401

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


async def recover_stale_datas():
    """Resets any datas that were 'in_progress' back to 'pending'."""
    logger.info("Checking for stale jobs to recover...")
    await reset_in_progress_jobs_to_pending()
    await reset_processing_links_to_pending()


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
    current_version: str
    latest_version: Optional[str] = None
    runtime_env: Literal["docker", "source"]
    update_available: bool


async def get_latest_github_version() -> Optional[str]:
    """Fetches the latest tag name from the GitHub repository."""
    # Use the /tags endpoint since the repo uses tags, not formal releases
    repo_url = "https://api.github.com/repos/bmen25124/lorebook-creator/tags"
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        async with httpx.AsyncClient() as client:
            # Get the list of tags; the API returns them in reverse chronological order
            response = await client.get(repo_url, headers=headers, timeout=5.0)
            response.raise_for_status()
            data = response.json()
            # The latest tag is the first one in the list
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get("name")
            else:
                logger.warning("No tags found in the GitHub repository.")
                return None
    except httpx.RequestError as e:
        logger.warning(f"Could not fetch latest version from GitHub: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching GitHub version: {e}")
        return None


@get(path="/info", sync_to_thread=False)
async def get_app_info() -> AppInfo:
    """Returns basic application information, including whether an update is available."""
    current_version = os.getenv("APP_VERSION", "development").split("-")[0]
    latest_version = await get_latest_github_version()
    runtime_env = os.getenv("RUNTIME_ENV", "source")

    update_available = False
    if (
        current_version != "development"
        and latest_version
        and current_version != latest_version
    ):
        update_available = True

    return AppInfo(
        current_version=current_version,
        latest_version=latest_version,
        runtime_env=runtime_env,  # pyright: ignore[reportArgumentType]
        update_available=update_available,
    )


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
            HealthController,
            ApiRequestLogController,
            ProviderController,
            SSEController,
            ProjectController,
            SourceController,
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
        on_startup=[create_default_templates, recover_stale_datas],
        on_shutdown=[close_database],
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

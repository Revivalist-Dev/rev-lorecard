import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List
import uuid

from controllers.sse import SSEController
from db.background_jobs import (
    BackgroundJob,
    TaskName,
    UpdateBackgroundJob,
    get_background_job,
    update_background_job,
)
from db.links import Link
from db.lorebook_entries import LorebookEntry
from logging_config import get_logger

logger = get_logger(__name__)

_rate_limit_tracker = defaultdict(list)  # project_id -> list of timestamps
_rate_limit_locks = defaultdict(asyncio.Lock)  # project_id -> asyncio.Lock


CONCURRENT_REQUESTS = 10


async def wait_for_rate_limit(project_id: str, requests_per_minute: int):
    """
    Waits if necessary to respect rate limiting.
    This function is thread-safe.
    """
    await _rate_limit_locks[project_id].acquire()
    try:
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)

        # Clean up old timestamps
        timestamps = _rate_limit_tracker[project_id]
        _rate_limit_tracker[project_id] = [
            ts for ts in timestamps if ts > one_minute_ago
        ]

        # Check if we need to wait
        if len(_rate_limit_tracker[project_id]) >= requests_per_minute:
            oldest_timestamp = min(_rate_limit_tracker[project_id])
            sleep_until = oldest_timestamp + timedelta(minutes=1)
            sleep_time = (sleep_until - now).total_seconds()

            if sleep_time > 0:
                logger.info(
                    f"Rate limit reached, sleeping for {sleep_time:.2f} seconds"
                )
                await asyncio.sleep(sleep_time)

        # Record the new request time *after* waiting
        _rate_limit_tracker[project_id].append(datetime.now())
    finally:
        _rate_limit_locks[project_id].release()


async def update_job_with_notification(
    job_id: uuid.UUID, job_update: UpdateBackgroundJob
) -> BackgroundJob:
    """Update job and send SSE notification."""
    updated_job = await update_background_job(job_id, job_update)
    if updated_job:
        await send_job_status_notification(updated_job)
    return updated_job  # pyright: ignore[reportReturnType]


async def send_job_status_notification(job: BackgroundJob):
    """Send SSE notification about job status change."""
    try:
        # Fetch the latest job state to include progress
        latest_job = await get_background_job(job.id)
        if latest_job:
            await SSEController.send_event_to_project(
                project_id=job.project_id,
                event_type="job_status_update",
                data=latest_job.model_dump(),
            )
    except Exception as e:
        logger.error(f"Error sending SSE notification: {e}", exc_info=True)


async def send_entry_created_notification(job: BackgroundJob, entry: LorebookEntry):
    """Send SSE notification about entry status change."""
    try:
        await SSEController.send_event_to_project(
            project_id=job.project_id,
            event_type="entry_created",
            data=entry.model_dump(),
        )
    except Exception as e:
        logger.error(f"Error sending SSE notification: {e}", exc_info=True)


async def send_links_created_notification(job: BackgroundJob, links: List[Link]):
    """Send SSE notification about link status change."""
    try:
        await SSEController.send_event_to_project(
            project_id=job.project_id,
            event_type="links_created",
            data={"links": [link.model_dump() for link in links]},
        )
    except Exception as e:
        logger.error(f"Error sending SSE notification: {e}", exc_info=True)


async def send_link_updated_notification(job: BackgroundJob, link: Link):
    """Send SSE notification about link status change."""
    try:
        await SSEController.send_event_to_project(
            project_id=job.project_id,
            event_type="link_updated",
            data=link.model_dump(),
        )
    except Exception as e:
        logger.error(f"Error sending SSE notification: {e}", exc_info=True)

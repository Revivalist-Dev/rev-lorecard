import asyncio

from db.background_jobs import (
    PARALLEL_LIMITS,
    JobStatus,
    UpdateBackgroundJob,
    count_in_progress_background_jobs_by_task_name,
    get_and_lock_pending_background_job,
    update_background_job,
)
from services.background_jobs import process_background_job
from logging_config import get_logger

logger = get_logger(__name__)


async def run_worker():
    """
    Main loop for the background worker.
    It continuously polls for pending jobs and processes them concurrently,
    respecting parallel limits for each task type.
    """
    logger.info("Starting background worker...")

    # Track active tasks by job ID
    active_tasks = {}

    while True:
        try:
            # Clean up completed tasks
            completed_tasks = []
            for task, job_id in active_tasks.items():
                if task.done():
                    completed_tasks.append(task)
                    try:
                        await task  # Raise exceptions if any
                        logger.info(f"Job {job_id} completed successfully.")
                    except Exception as e:
                        logger.error(
                            f"Job {job_id} failed with an exception: {e}",
                            exc_info=True,
                        )

            # Remove completed tasks
            for task in completed_tasks:
                del active_tasks[task]

            # Check if we can schedule more jobs
            max_workers = sum(PARALLEL_LIMITS.values())

            if len(active_tasks) < max_workers:
                # Use the new atomic function to get and lock a job
                job = await get_and_lock_pending_background_job()
                if job:
                    task_name = job.task_name
                    limit = PARALLEL_LIMITS.get(task_name, 1)
                    # We check active_jobs *after* successfully claiming one
                    active_jobs_for_task = (
                        await count_in_progress_background_jobs_by_task_name(task_name)
                    )

                    if (
                        active_jobs_for_task <= limit
                    ):  # Check is now <= because we already set one to in_progress
                        logger.info(
                            f"Worker: Submitting job {job.id} (Task: {task_name.value}, "
                            f"Active: {active_jobs_for_task}, Limit: {limit})"
                        )
                        task = asyncio.create_task(process_background_job(job.id))
                        active_tasks[task] = job.id
                    else:
                        # This case is less likely now but good for safety.
                        # We claimed a job but the limit for its type is full.
                        # Revert its status back to pending.
                        logger.warning(
                            f"Limit for {task_name.value} reached. Re-queueing job {job.id}"
                        )

                        await update_background_job(
                            job.id, UpdateBackgroundJob(status=JobStatus.pending)
                        )
                        await asyncio.sleep(2)
                else:
                    logger.debug("No pending jobs found. Still polling.")
                    await asyncio.sleep(2)
            else:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Worker main loop encountered an error: {e}", exc_info=True)
            await asyncio.sleep(4)

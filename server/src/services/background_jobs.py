import asyncio
import hashlib
from uuid import UUID
from datetime import datetime
from typing import Optional, Union, List, Dict

from urllib.parse import urljoin
from bs4 import BeautifulSoup
from pydantic import BaseModel
from db.background_jobs import (
    BackgroundJob,
    ConfirmLinksPayload,
    ConfirmLinksResult,
    GenerateSelectorPayload,
    GenerateSelectorResult,
    GenerateSearchParamsResult,
    JobStatus,
    ProcessProjectEntriesPayload,
    ProcessProjectEntriesResult,
    TaskName,
    UpdateBackgroundJob,
    get_background_job,
)
from db.connection import get_db_connection
from db.database import AsyncDBTransaction
from db.links import (
    CreateLink,
    Link,
    LinkStatus,
    UpdateLink,
    create_links,
    get_existing_links_by_urls,
    get_link,
    get_processable_links_for_project,
    update_link,
)
from db.lorebook_entries import CreateLorebookEntry, create_lorebook_entry
from db.projects import (
    Project,
    ProjectStatus,
    SearchParams,
    UpdateProject,
    get_project,
    update_project,
)
from db.sources import (
    ProjectSource,
    UpdateProjectSource,
    get_project_source,
    update_project_source,
)
from db.global_templates import list_all_global_templates
from providers.index import (
    ChatCompletionErrorResponse,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ResponseSchema,
    get_provider,
)
from schemas import LorebookEntryResponse, SearchParamsResponse, SelectorResponse
from services.rate_limiter import (
    CONCURRENT_REQUESTS,
    send_entry_created_notification,
    send_link_updated_notification,
    send_links_created_notification,
    update_job_with_notification,
    wait_for_rate_limit,
)
from db.api_request_logs import create_api_request_log, CreateApiRequestLog
from services.scraper import Scraper, html_to_markdown
from logging_config import get_logger
from services.templates import create_messages_from_template

logger = get_logger(__name__)

# Process database writes in chunks of this size for better UI feedback.
DB_WRITE_BATCH_SIZE = 10

# --- Result Models for Concurrent Processing ---
# These models are used to pass results from the I/O-bound phase to the DB-bound phase.


class LinkSuccessResult(BaseModel):
    link_id: UUID
    entry_payload: CreateLorebookEntry
    log_payload: CreateApiRequestLog
    raw_content: str


class LinkSkippedResult(BaseModel):
    link_id: UUID
    reason: str
    log_payload: CreateApiRequestLog


class LinkFailedResult(BaseModel):
    link_id: UUID
    error_message: str
    log_payload: Optional[CreateApiRequestLog] = None


LinkProcessingResult = Union[LinkSuccessResult, LinkSkippedResult, LinkFailedResult]


async def _crawl_one_source(
    job_id: UUID, source: ProjectSource, tx: AsyncDBTransaction
) -> list[str]:
    """Crawls a single source URL and returns a list of found links."""
    scraper = Scraper()

    selectors = source.link_extraction_selector
    pagination_selector = source.link_extraction_pagination_selector

    if not selectors:
        logger.warning(
            f"[{job_id}] Source {source.id} has no selectors for crawling. Skipping."
        )
        return []

    logger.info(
        f"[{job_id}] Starting crawl for source {source.id} using selectors: {selectors}"
    )

    current_url: str | None = source.url
    found_links_set = set()
    visited_content_hashes = set()
    pages_crawled = 0

    while current_url and pages_crawled < source.max_pages_to_crawl:
        pages_crawled += 1
        logger.info(
            f"[{job_id}] Crawling page {pages_crawled} of source {source.id}: {current_url}"
        )

        try:
            html = await scraper.get_content(current_url, clean=True)
            markdown = html_to_markdown(html)
        except Exception as e:
            logger.error(f"Failed to fetch {current_url}: {e}")
            break

        content_hash = hashlib.md5(markdown.encode()).hexdigest()
        if content_hash in visited_content_hashes:
            logger.info(
                f"[{job_id}] Duplicate page content detected for source {source.id}. Ending crawl."
            )
            break
        visited_content_hashes.add(content_hash)

        soup = BeautifulSoup(html, "html.parser")

        # Extract content links
        for selector in selectors:
            for link in soup.select(selector):
                if href := link.get("href"):
                    absolute_url = urljoin(str(current_url), href)  # pyright: ignore[reportArgumentType]
                    found_links_set.add(absolute_url)

        # Find next page link
        next_page_url = None
        if pagination_selector:
            if next_page_element := soup.select_one(pagination_selector):
                if href := next_page_element.get("href"):
                    next_page_url = urljoin(str(current_url), href)  # pyright: ignore[reportArgumentType]

        if next_page_url == current_url:
            break
        current_url = next_page_url

    await update_project_source(
        source.id, UpdateProjectSource(last_crawled_at=datetime.now()), tx=tx
    )

    return sorted(list(found_links_set))


async def generate_selector(job: BackgroundJob, project: Project):
    if not isinstance(job.payload, GenerateSelectorPayload):
        raise TypeError("Invalid payload for generate_selector job.")

    async with (await get_db_connection()).transaction() as tx:
        source_ids = job.payload.source_ids
        total_sources = len(source_ids)
        processed_sources = 0
        all_found_urls_set = set()
        all_selectors: dict[str, list[str]] = {}
        all_pagination_selectors: dict[str, Optional[str]] = {}

        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                total_items=total_sources, processed_items=0, progress=0
            ),
            tx=tx,
        )

        for source_id in source_ids:
            source = await get_project_source(source_id, tx=tx)
            if not source:
                logger.warning(f"[{job.id}] Source {source_id} not found, skipping.")
                continue

            if not project.search_params:
                raise ValueError("Project must have search params")

            scraper = Scraper()
            logger.info(f"[{job.id}] Scraping content from {source.url}")
            content = await scraper.get_content(source.url, clean=True, pretty=True)
            provider = get_provider(project.ai_provider_config.api_provider)
            logger.info(
                f"[{job.id}] Generating selector for source {source.id} with {provider.__class__.__name__}"
            )

            global_templates = await list_all_global_templates(tx=tx)
            globals_dict = {gt.name: gt.content for gt in global_templates}
            context = {
                "content": content,
                "project": project.model_dump(),
                "source": source.model_dump(),
                "globals": globals_dict,
            }
            response = await provider.generate(
                ChatCompletionRequest(
                    model=project.ai_provider_config.model_name,
                    messages=create_messages_from_template(
                        project.templates.selector_generation, context
                    ),
                    response_format=ResponseSchema(
                        name="selector_response",
                        schema_value=SelectorResponse.model_json_schema(),
                    ),
                    **project.ai_provider_config.model_parameters,
                )
            )

            if isinstance(response, ChatCompletionErrorResponse):
                await create_api_request_log(
                    CreateApiRequestLog(
                        project_id=project.id,
                        job_id=job.id,
                        api_provider=project.ai_provider_config.api_provider,
                        model_used=project.ai_provider_config.model_name,
                        request=response.raw_request,
                        response=response.raw_response,
                        latency_ms=response.latency_ms,
                        error=True,
                    )
                )
                raise Exception(
                    f"Failed to generate selector for source {source.id}: {response.raw_response}"
                )

            await create_api_request_log(
                CreateApiRequestLog(
                    project_id=project.id,
                    job_id=job.id,
                    api_provider=project.ai_provider_config.api_provider,
                    model_used=project.ai_provider_config.model_name,
                    request=response.raw_request,
                    response=response.raw_response,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    calculated_cost=response.usage.cost,
                    latency_ms=response.latency_ms,
                )
            )

            selector_response = SelectorResponse.model_validate(response.content)
            update_payload = UpdateProjectSource(
                link_extraction_selector=selector_response.selectors,
                link_extraction_pagination_selector=selector_response.pagination_selector,
            )
            if project.status == ProjectStatus.search_params_generated:
                await update_project(
                    project.id,
                    UpdateProject(status=ProjectStatus.selector_generated),
                    tx=tx,
                )

            updated_source = await update_project_source(
                source.id, update_payload, tx=tx
            )
            if not updated_source:
                raise Exception(
                    f"Failed to update project source {source.id} with new selectors."
                )

            source_urls = await _crawl_one_source(job.id, updated_source, tx=tx)
            all_found_urls_set.update(source_urls)
            all_selectors[str(source.id)] = (
                updated_source.link_extraction_selector or []
            )
            all_pagination_selectors[str(source.id)] = (
                updated_source.link_extraction_pagination_selector
            )

            processed_sources += 1
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    processed_items=processed_sources,
                    progress=(processed_sources / total_sources) * 100,
                ),
                tx=tx,
            )

        all_found_urls = sorted(list(all_found_urls_set))
        existing_urls_in_db = await get_existing_links_by_urls(
            project.id, all_found_urls, tx=tx
        )
        existing_urls_set = set(existing_urls_in_db)
        new_urls = [url for url in all_found_urls if url not in existing_urls_set]

        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.completed,
                result=GenerateSelectorResult(
                    new_urls=new_urls,
                    existing_urls=sorted(list(existing_urls_set)),
                    selectors=all_selectors,
                    pagination_selectors=all_pagination_selectors,
                ),
            ),
            tx=tx,
        )


async def rescan_links(job: BackgroundJob, project: Project):
    """Process a job to rescan for links using existing selectors for multiple sources."""
    if not isinstance(job.payload, GenerateSelectorPayload):
        raise TypeError("Invalid payload for rescan_links job.")

    async with (await get_db_connection()).transaction() as tx:
        source_ids = job.payload.source_ids
        total_sources = len(source_ids)
        processed_sources = 0
        all_found_urls_set = set()
        all_selectors: dict[str, list[str]] = {}
        all_pagination_selectors: dict[str, Optional[str]] = {}

        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                total_items=total_sources, processed_items=0, progress=0
            ),
            tx=tx,
        )

        for source_id in source_ids:
            source = await get_project_source(source_id, tx=tx)
            if not source:
                logger.warning(f"[{job.id}] Source {source_id} not found, skipping.")
                continue

            if not source.link_extraction_selector:
                logger.warning(
                    f"[{job.id}] Source {source.id} has no selectors, skipping rescan."
                )
                continue

            source_urls = await _crawl_one_source(job.id, source, tx=tx)
            all_found_urls_set.update(source_urls)
            all_selectors[str(source.id)] = source.link_extraction_selector
            all_pagination_selectors[str(source.id)] = (
                source.link_extraction_pagination_selector
            )

            processed_sources += 1
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    processed_items=processed_sources,
                    progress=(processed_sources / total_sources) * 100,
                ),
                tx=tx,
            )

        all_found_urls = sorted(list(all_found_urls_set))
        existing_urls_in_db = await get_existing_links_by_urls(
            project.id, all_found_urls, tx=tx
        )
        existing_urls_set = set(existing_urls_in_db)
        new_urls = [url for url in all_found_urls if url not in existing_urls_set]

        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.completed,
                result=GenerateSelectorResult(
                    new_urls=new_urls,
                    existing_urls=sorted(list(existing_urls_set)),
                    selectors=all_selectors,
                    pagination_selectors=all_pagination_selectors,
                ),
            ),
            tx=tx,
        )


async def generate_search_params(job: BackgroundJob, project: Project):
    if not project.prompt:
        raise ValueError("Project must have a prompt")

    async with (await get_db_connection()).transaction() as tx:
        provider = get_provider(project.ai_provider_config.api_provider)
        logger.info(
            f"[{job.id}] Generating search params with {provider.__class__.__name__}"
        )

        global_templates = await list_all_global_templates(tx=tx)
        globals_dict = {gt.name: gt.content for gt in global_templates}
        context = {"project": project.model_dump(), "globals": globals_dict}
        response = await provider.generate(
            ChatCompletionRequest(
                model=project.ai_provider_config.model_name,
                messages=create_messages_from_template(
                    project.templates.search_params_generation,
                    context,
                ),
                response_format=ResponseSchema(
                    name="search_params_response",
                    schema_value=SearchParamsResponse.model_json_schema(),
                ),
                **project.ai_provider_config.model_parameters,
            )
        )

        if isinstance(response, ChatCompletionErrorResponse):
            await create_api_request_log(
                CreateApiRequestLog(
                    project_id=project.id,
                    job_id=job.id,
                    api_provider=project.ai_provider_config.api_provider,
                    model_used=project.ai_provider_config.model_name,
                    request=response.raw_request,
                    response=response.raw_response,
                    latency_ms=response.latency_ms,
                    error=True,
                )
            )
            raise Exception(
                f"Failed to generate search_params: {response.raw_response}"
            )

        await create_api_request_log(
            CreateApiRequestLog(
                project_id=project.id,
                job_id=job.id,
                api_provider=project.ai_provider_config.api_provider,
                model_used=project.ai_provider_config.model_name,
                request=response.raw_request,
                response=response.raw_response,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                calculated_cost=response.usage.cost,
                latency_ms=response.latency_ms,
            )
        )

        search_params_response = SearchParamsResponse.model_validate(response.content)
        update_payload = UpdateProject(
            search_params=SearchParams(
                purpose=search_params_response.purpose,
                extraction_notes=search_params_response.extraction_notes,
                criteria=search_params_response.criteria,
            )
        )
        if project.status == ProjectStatus.draft:
            update_payload.status = ProjectStatus.search_params_generated
        await update_project(project.id, update_payload, tx=tx)
        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.completed,
                result=GenerateSearchParamsResult(),
            ),
            tx=tx,
        )


async def confirm_links(job: BackgroundJob, project: Project):
    if not isinstance(job.payload, ConfirmLinksPayload):
        raise Exception("Invalid payload for confirm_links task")

    async with (await get_db_connection()).transaction() as tx:
        if not job.payload.urls:
            logger.warning(f"[{job.id}] Confirm links job received no URLs to save.")
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    status=JobStatus.completed,
                    result=ConfirmLinksResult(links_saved=0),
                ),
                tx=tx,
            )
            return

        links_to_create = [
            CreateLink(project_id=project.id, url=url) for url in job.payload.urls
        ]

        links = await create_links(links_to_create, tx=tx)
        await send_links_created_notification(job, links)
        if project.status == ProjectStatus.selector_generated:
            await update_project(
                project.id, UpdateProject(status=ProjectStatus.links_extracted), tx=tx
            )
        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.completed,
                result=ConfirmLinksResult(links_saved=len(links_to_create)),
            ),
            tx=tx,
        )


async def _process_single_link_io(
    job: BackgroundJob, project: Project, link: Link, scraper: Scraper
) -> LinkProcessingResult:
    """
    Phase 1 of processing a link: Perform all I/O-bound operations (scraping, LLM call).
    This function DOES NOT write to the database. It returns a result object with all
    the necessary data for the database write phase.
    """
    log_payload: Optional[CreateApiRequestLog] = None
    try:
        content = (
            link.raw_content
            if link.raw_content
            else await scraper.get_content(link.url, type="markdown", clean=True)
        )
        provider = get_provider(project.ai_provider_config.api_provider)

        global_templates = await list_all_global_templates()
        globals_dict = {gt.name: gt.content for gt in global_templates}
        context = {
            "project": project.model_dump(),
            "content": content,
            "source": link.model_dump(),
            "globals": globals_dict,
        }
        response = await provider.generate(
            ChatCompletionRequest(
                model=project.ai_provider_config.model_name,
                messages=create_messages_from_template(
                    project.templates.entry_creation, context
                ),
                response_format=ResponseSchema(
                    name="lorebook_entry_response",
                    schema_value=LorebookEntryResponse.model_json_schema(),
                ),
                **project.ai_provider_config.model_parameters,
            )
        )

        is_error = isinstance(response, ChatCompletionErrorResponse)
        usage = response.usage if isinstance(response, ChatCompletionResponse) else None
        log_payload = CreateApiRequestLog(
            project_id=project.id,
            job_id=job.id,
            api_provider=project.ai_provider_config.api_provider,
            model_used=project.ai_provider_config.model_name,
            request=response.raw_request,
            response=response.raw_response,
            latency_ms=response.latency_ms,
            error=is_error,
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
            calculated_cost=usage.cost if usage else None,
        )

        if is_error:
            raise Exception(f"Failed to generate entry: {response.raw_response}")

        entry_response = LorebookEntryResponse.model_validate(response.content)

        if entry_response.valid and entry_response.entry:
            entry_payload = CreateLorebookEntry(
                project_id=project.id,
                title=entry_response.entry.title,
                content=entry_response.entry.content,
                keywords=entry_response.entry.keywords,
                source_url=link.url,
            )
            return LinkSuccessResult(
                link_id=link.id,
                entry_payload=entry_payload,
                log_payload=log_payload,
                raw_content=content,
            )
        else:
            reason = entry_response.reason or "Content did not meet project criteria."
            return LinkSkippedResult(
                link_id=link.id, reason=reason, log_payload=log_payload
            )

    except Exception as e:
        logger.error(
            f"[{job.id}] I/O phase error processing link {link.id}: {e}", exc_info=True
        )
        return LinkFailedResult(
            link_id=link.id, error_message=str(e), log_payload=log_payload
        )


async def _process_db_batch(
    job: BackgroundJob,
    batch_results: List[LinkProcessingResult],
) -> Dict[str, int]:
    """
    Phase 2 helper: Processes a batch of results and writes them to the DB
    within a single transaction.
    """
    counts = {"created": 0, "skipped": 0, "failed": 0}
    async with (await get_db_connection()).transaction() as tx:
        for result in batch_results:
            if result.log_payload:
                await create_api_request_log(result.log_payload)

            if isinstance(result, LinkSuccessResult):
                created_entry = await create_lorebook_entry(result.entry_payload, tx=tx)
                await update_link(
                    result.link_id,
                    UpdateLink(
                        status=LinkStatus.completed,
                        lorebook_entry_id=created_entry.id,
                        raw_content=result.raw_content,
                    ),
                    tx=tx,
                )
                await send_entry_created_notification(job, created_entry)
                counts["created"] += 1
            elif isinstance(result, LinkSkippedResult):
                await update_link(
                    result.link_id,
                    UpdateLink(status=LinkStatus.skipped, skip_reason=result.reason),
                    tx=tx,
                )
                counts["skipped"] += 1
            elif isinstance(result, LinkFailedResult):
                await update_link(
                    result.link_id,
                    UpdateLink(
                        status=LinkStatus.failed, error_message=result.error_message
                    ),
                    tx=tx,
                )
                counts["failed"] += 1

            updated_link = await get_link(result.link_id, tx=tx)
            if updated_link:
                await send_link_updated_notification(job, updated_link)
    return counts


async def process_project_entries(job: BackgroundJob, project: Project):
    """
    Process all pending links for a project to generate lorebook entries using a
    concurrent I/O phase and a batched, transactional database write phase.
    """
    if not isinstance(job.payload, ProcessProjectEntriesPayload):
        raise Exception("Invalid payload for process_project_entries task")

    scraper = Scraper()
    pending_links = await get_processable_links_for_project(project.id)
    total_links = len(pending_links)

    if not total_links:
        # Handle case with no links to process
        async with (await get_db_connection()).transaction() as tx:
            await update_project(
                project.id, UpdateProject(status=ProjectStatus.completed), tx=tx
            )
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    status=JobStatus.completed,
                    progress=100,
                    result=ProcessProjectEntriesResult(
                        entries_created=0, entries_failed=0, entries_skipped=0
                    ),
                ),
                tx=tx,
            )
        return

    # Initial job and project status updates
    async with (await get_db_connection()).transaction() as tx:
        await update_project(
            project.id, UpdateProject(status=ProjectStatus.processing), tx=tx
        )
        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                total_items=total_links, processed_items=0, progress=0.0
            ),
            tx=tx,
        )
        for link in pending_links:
            await update_link(link.id, UpdateLink(status=LinkStatus.processing), tx=tx)
            updated_link = await get_link(link.id, tx=tx)
            if updated_link:
                await send_link_updated_notification(job, updated_link)

    # --- Phase 1 & 2: Concurrent I/O and Batched DB Writes ---
    cancellation_event = asyncio.Event()
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def poll_for_cancellation():
        while not cancellation_event.is_set():
            try:
                current_job = await get_background_job(job.id)
                if current_job and current_job.status == JobStatus.cancelling:
                    cancellation_event.set()
                    break
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break

    polling_task = asyncio.create_task(poll_for_cancellation())

    async def process_with_limiter(link: Link) -> Optional[LinkProcessingResult]:
        if cancellation_event.is_set():
            return None
        async with semaphore:
            await wait_for_rate_limit(project.id, project.requests_per_minute)
            if cancellation_event.is_set():
                return None
            return await _process_single_link_io(job, project, link, scraper)

    tasks = [asyncio.create_task(process_with_limiter(link)) for link in pending_links]

    batch_results: List[LinkProcessingResult] = []
    total_processed = 0
    total_created = 0
    total_skipped = 0
    total_failed = 0

    for future in asyncio.as_completed(tasks):
        result = await future
        if result:
            batch_results.append(result)

        # Process a batch when it's full or when all tasks are done
        if len(batch_results) >= DB_WRITE_BATCH_SIZE or (
            total_processed + len(batch_results) == total_links
        ):
            if not batch_results:
                continue

            counts = await _process_db_batch(job, batch_results)
            total_created += counts["created"]
            total_skipped += counts["skipped"]
            total_failed += counts["failed"]
            total_processed += len(batch_results)
            batch_results.clear()

            # Update overall job progress after each batch is written
            progress = (total_processed / total_links) * 100
            async with (await get_db_connection()).transaction() as tx:
                await update_job_with_notification(
                    job.id,
                    UpdateBackgroundJob(
                        processed_items=total_processed, progress=progress
                    ),
                    tx=tx,
                )

    polling_task.cancel()

    # --- Finalization Phase ---
    async with (await get_db_connection()).transaction() as tx:
        if cancellation_event.is_set():
            await update_job_with_notification(
                job.id, UpdateBackgroundJob(status=JobStatus.canceled), tx=tx
            )
            await tx.execute(
                "UPDATE \"Link\" SET status = 'pending' WHERE project_id = %s AND status = 'processing'",
                (project.id,),
            )
        else:
            final_project_status = (
                ProjectStatus.completed if total_failed == 0 else ProjectStatus.failed
            )
            await update_project(
                project.id, UpdateProject(status=final_project_status), tx=tx
            )
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    status=JobStatus.completed,
                    result=ProcessProjectEntriesResult(
                        entries_created=total_created,
                        entries_failed=total_failed,
                        entries_skipped=total_skipped,
                    ),
                ),
                tx=tx,
            )


async def process_background_job(id: UUID):
    job = await get_background_job(id)
    if not job:
        return

    if not job.project_id:
        logger.error(f"[{job.id}] Job has no project_id")
        return

    project = await get_project(job.project_id)
    if not project:
        logger.error(f"[{job.id}] Project not found: {job.project_id}")
        return

    try:
        if job.task_name == TaskName.GENERATE_SELECTOR:
            await generate_selector(job, project)
        elif job.task_name == TaskName.RESCAN_LINKS:
            await rescan_links(job, project)
        elif job.task_name == TaskName.CONFIRM_LINKS:
            await confirm_links(job, project)
        elif job.task_name == TaskName.PROCESS_PROJECT_ENTRIES:
            await process_project_entries(job, project)
        elif job.task_name == TaskName.GENERATE_SEARCH_PARAMS:
            await generate_search_params(job, project)
    except Exception as e:
        logger.error(f"[{job.id}] Error processing job: {e}", exc_info=True)
        async with (await get_db_connection()).transaction() as tx:
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    status=JobStatus.failed,
                    error_message=str(e),
                ),
                tx=tx,
            )

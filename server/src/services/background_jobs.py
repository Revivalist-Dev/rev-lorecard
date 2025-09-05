import asyncio
from uuid import UUID
from datetime import datetime
from typing import Optional, Union, List, Dict, Set
from pydantic import BaseModel
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from collections import deque

from soupsieve import SelectorSyntaxError

from db.background_jobs import (
    BackgroundJob,
    ConfirmLinksPayload,
    ConfirmLinksResult,
    DiscoverAndCrawlSourcesPayload,
    DiscoverAndCrawlSourcesResult,
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
    get_all_link_urls_for_project,
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
    CreateProjectSource,
    ProjectSource,
    UpdateProjectSource,
    create_project_source,
    get_project_source,
    get_project_source_by_url,
    update_project_source,
)
from db.source_hierarchy import add_source_child_relationship
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
from services.scraper import Scraper
from logging_config import get_logger
from services.templates import create_messages_from_template

logger = get_logger(__name__)

# Process database writes in chunks of this size for better UI feedback.
DB_WRITE_BATCH_SIZE = 10


# --- Result Models for Concurrent Processing ---
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


class CrawlResult(BaseModel):
    new_links: Set[str] = set()
    existing_links: Set[str] = set()
    new_sources_created: int = 0


async def _crawl_and_discover(
    project_id: str,
    source: ProjectSource,
    selectors: SelectorResponse,
    queue: deque,
    visited_source_urls: Set[str],
    current_depth: int,
    scraper: Scraper,
    existing_db_links: Set[str],
    newly_discovered_links_this_job: Set[str],
    tx: AsyncDBTransaction,
) -> CrawlResult:
    """
    Internal helper to perform crawling and discovery for a single source
    """
    result = CrawlResult()
    pages_crawled = 0
    current_url: Optional[str] = source.url

    while current_url and pages_crawled < source.max_pages_to_crawl:
        logger.info(
            f"[{source.project_id}] Crawling page {pages_crawled + 1} of source {source.id}: {current_url}"
        )
        content = await scraper.get_content(current_url, clean=True, pretty=True)
        soup = BeautifulSoup(content, "html.parser")
        pages_crawled += 1

        # --- 1. Extract all potential content and category URLs from the current page ---
        content_urls = set()
        for selector in selectors.content_selectors:
            try:
                for link_tag in soup.select(selector):
                    if href := link_tag.get("href"):
                        content_urls.add(urljoin(current_url, href))  # pyright: ignore[reportArgumentType]
            except SelectorSyntaxError as e:
                logger.warning(
                    f"Invalid content CSS selector '{selector}' for source {source.url}. Skipping. Error: {e}"
                )

        category_urls = set()
        if current_depth < source.max_crawl_depth:
            for selector in selectors.category_selectors:
                try:
                    for link_tag in soup.select(selector):
                        if href := link_tag.get("href"):
                            category_urls.add(urljoin(current_url, href))  # pyright: ignore[reportArgumentType]
                except SelectorSyntaxError as e:
                    logger.warning(
                        f"Invalid category CSS selector '{selector}' for source {source.url}. Skipping. Error: {e}"
                    )

        # --- 2. Differentiate new vs. existing links ---
        content_urls -= (
            category_urls  # Ensure content links are not also treated as categories
        )
        for url in content_urls:
            if url in existing_db_links:
                result.existing_links.add(url)
            elif url not in newly_discovered_links_this_job:
                result.new_links.add(url)

        # --- 3. Process Discovered Sub-category Links and Enqueue (only on the first page) ---
        if pages_crawled == 1 and current_depth < source.max_crawl_depth:
            for cat_url in category_urls:
                if cat_url not in visited_source_urls:
                    visited_source_urls.add(cat_url)
                    existing_source = await get_project_source_by_url(
                        project_id, cat_url, tx=tx
                    )

                    if existing_source:
                        child_source = existing_source
                    else:
                        child_source = await create_project_source(
                            CreateProjectSource(
                                project_id=project_id,
                                url=cat_url,
                                max_crawl_depth=source.max_crawl_depth,
                                max_pages_to_crawl=source.max_pages_to_crawl,
                            ),
                            tx=tx,
                        )
                        result.new_sources_created += 1

                    await add_source_child_relationship(
                        project_id, source.id, child_source.id, tx=tx
                    )
                    queue.append((child_source.id, current_depth + 1))

        # --- 4. Find the next page URL ---
        if selectors.pagination_selector:
            next_page_tag = soup.select_one(selectors.pagination_selector)
            if next_page_tag and next_page_tag.get("href"):
                next_page_url = urljoin(current_url, next_page_tag.get("href"))  # pyright: ignore[reportArgumentType]
                # Prevent infinite loops on pages that link to themselves as 'next'
                if next_page_url == current_url:
                    current_url = None
                else:
                    current_url = next_page_url
            else:
                current_url = None  # No more 'next' page link found
        else:
            current_url = None  # No pagination selector was provided

    # --- 5. Update Source's Last Crawled Time ---
    await update_project_source(
        source.id, UpdateProjectSource(last_crawled_at=datetime.now()), tx=tx
    )
    return result


async def discover_and_crawl_sources(job: BackgroundJob, project: Project):
    """
    Processes a job to discover sub-sources and find content links, without saving them.
    The found URLs are returned in the job result.
    """
    if not isinstance(job.payload, DiscoverAndCrawlSourcesPayload):
        raise TypeError("Invalid payload for discover_and_crawl_sources job.")
    if not project.search_params:
        raise ValueError("Project must have search params to discover sources.")

    # --- Cancellation Setup ---
    cancellation_event = asyncio.Event()

    async def poll_for_cancellation():
        while not cancellation_event.is_set():
            try:
                current_job = await get_background_job(job.id)
                if current_job and current_job.status == JobStatus.cancelling:
                    cancellation_event.set()
                    logger.info(
                        f"[{job.id}] Cancellation requested for discover & crawl job."
                    )
                    break
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break

    polling_task = asyncio.create_task(poll_for_cancellation())

    # --- Job State Initialization ---
    db = await get_db_connection()
    existing_db_links = set(await get_all_link_urls_for_project(project.id))
    queue: deque[tuple[UUID, int]] = deque()
    visited_source_urls: Set[str] = set()
    all_new_links_this_job: Set[str] = set()
    all_existing_links_found_again: Set[str] = set()
    total_new_sources = 0
    total_selectors_generated = 0
    processed_count = 0

    async with db.transaction() as tx:
        for source_id in job.payload.source_ids:
            source = await get_project_source(source_id, tx=tx)
            if source:
                queue.append((source.id, 1))
                visited_source_urls.add(source.url)
        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(total_items=len(queue), processed_items=0, progress=0),
            tx=tx,
        )

    scraper = Scraper()
    provider = get_provider(project.ai_provider_config.api_provider)
    global_templates = await list_all_global_templates()
    globals_dict = {gt.name: gt.content for gt in global_templates}

    while queue:
        if cancellation_event.is_set():
            logger.info(
                f"[{job.id}] Breaking discover & crawl loop due to cancellation."
            )
            break

        source_id, current_depth = queue.popleft()
        source = await get_project_source(source_id)
        if not source:
            continue

        # --- 1. Generate Selectors via LLM ---
        logger.info(
            f"[{job.id}] Generating selectors for source {source.id} at depth {current_depth}"
        )
        content = await scraper.get_content(source.url, clean=True, pretty=True)
        context = {
            "content": content,
            "project": project.model_dump(),
            "source": source.model_dump(),
            "globals": globals_dict,
        }
        await wait_for_rate_limit(project.id, project.requests_per_minute)
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

        # --- DB Write Phase for this source ---
        async with db.transaction() as tx:
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
                    ),
                )
                raise Exception(
                    f"Failed to generate selectors for source {source.id}: {response.raw_response}"
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
                ),
            )

            total_selectors_generated += 1
            selector_response = SelectorResponse.model_validate(response.content)
            await update_project_source(
                source.id,
                UpdateProjectSource(
                    link_extraction_selector=selector_response.content_selectors,
                    link_extraction_pagination_selector=selector_response.pagination_selector,
                ),
                tx=tx,
            )

            # --- 2. Crawl using the new selectors ---
            crawl_result = await _crawl_and_discover(
                project.id,
                source,
                selector_response,
                queue,
                visited_source_urls,
                current_depth,
                scraper,
                existing_db_links,
                all_new_links_this_job,
                tx,
            )
            all_new_links_this_job.update(crawl_result.new_links)
            all_existing_links_found_again.update(crawl_result.existing_links)
            total_new_sources += crawl_result.new_sources_created

            # --- 3. Update Job Progress ---
            processed_count += 1
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    processed_items=processed_count,
                    total_items=len(visited_source_urls),
                ),
                tx=tx,
            )

    polling_task.cancel()
    # --- Finalization Phase ---
    async with db.transaction() as tx:
        if cancellation_event.is_set():
            await update_job_with_notification(
                job.id, UpdateBackgroundJob(status=JobStatus.canceled), tx=tx
            )
            return

        if project.status == ProjectStatus.search_params_generated:
            await update_project(
                project.id,
                UpdateProject(status=ProjectStatus.selector_generated),
                tx=tx,
            )

        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.completed,
                progress=100,
                result=DiscoverAndCrawlSourcesResult(
                    new_links=sorted(list(all_new_links_this_job)),
                    existing_links=sorted(list(all_existing_links_found_again)),
                    new_sources_created=total_new_sources,
                    selectors_generated=total_selectors_generated,
                ),
            ),
            tx=tx,
        )


async def rescan_links(job: BackgroundJob, project: Project):
    """
    Processes a job to re-crawl sources using existing selectors, without LLM calls.
    Found URLs are returned in the job result.
    """
    if not isinstance(job.payload, DiscoverAndCrawlSourcesPayload):
        raise TypeError("Invalid payload for rescan_links job.")

    # --- Cancellation Setup ---
    cancellation_event = asyncio.Event()

    async def poll_for_cancellation():
        while not cancellation_event.is_set():
            try:
                current_job = await get_background_job(job.id)
                if current_job and current_job.status == JobStatus.cancelling:
                    cancellation_event.set()
                    logger.info(f"[{job.id}] Cancellation requested for rescan job.")
                    break
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break

    polling_task = asyncio.create_task(poll_for_cancellation())

    # --- Job State Initialization ---
    db = await get_db_connection()
    existing_db_links = set(await get_all_link_urls_for_project(project.id))
    queue: deque[tuple[UUID, int]] = deque()
    visited_source_urls: Set[str] = set()
    all_new_links_this_job: Set[str] = set()
    all_existing_links_found_again: Set[str] = set()
    total_new_sources = 0
    processed_count = 0

    async with db.transaction() as tx:
        for source_id in job.payload.source_ids:
            source = await get_project_source(source_id, tx=tx)
            if source:
                queue.append((source.id, 1))
                visited_source_urls.add(source.url)

        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(total_items=len(queue), processed_items=0, progress=0),
            tx=tx,
        )

    scraper = Scraper()

    while queue:
        if cancellation_event.is_set():
            logger.info(f"[{job.id}] Breaking rescan loop due to cancellation.")
            break

        source_id, current_depth = queue.popleft()
        source = await get_project_source(source_id)
        if not source or not source.link_extraction_selector:
            logger.warning(
                f"[{job.id}] Source {source_id} has no selectors, skipping rescan."
            )
            continue

        logger.info(
            f"[{job.id}] Rescanning source {source.id} at depth {current_depth}"
        )

        async with db.transaction() as tx:
            # --- 1. Crawl using existing selectors ---
            selectors = SelectorResponse(
                content_selectors=source.link_extraction_selector,
                category_selectors=[],
                pagination_selector=source.link_extraction_pagination_selector,
            )
            crawl_result = await _crawl_and_discover(
                project.id,
                source,
                selectors,
                queue,
                visited_source_urls,
                current_depth,
                scraper,
                existing_db_links,
                all_new_links_this_job,
                tx,
            )
            all_new_links_this_job.update(crawl_result.new_links)
            all_existing_links_found_again.update(crawl_result.existing_links)
            total_new_sources += crawl_result.new_sources_created

            # --- 2. Update Job Progress ---
            processed_count += 1
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    processed_items=processed_count,
                    total_items=len(visited_source_urls),
                ),
                tx=tx,
            )

    polling_task.cancel()
    # --- Finalization Phase ---
    async with db.transaction() as tx:
        if cancellation_event.is_set():
            await update_job_with_notification(
                job.id, UpdateBackgroundJob(status=JobStatus.canceled), tx=tx
            )
            return

        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.completed,
                progress=100,
                result=DiscoverAndCrawlSourcesResult(
                    new_links=sorted(list(all_new_links_this_job)),
                    existing_links=sorted(list(all_existing_links_found_again)),
                    new_sources_created=total_new_sources,
                    selectors_generated=0,
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
                ),
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
            ),
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
        if job.task_name == TaskName.DISCOVER_AND_CRAWL_SOURCES:
            await discover_and_crawl_sources(job, project)
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

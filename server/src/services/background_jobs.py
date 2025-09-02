import asyncio
import hashlib
from uuid import UUID

from urllib.parse import urljoin
from bs4 import BeautifulSoup
from db.background_jobs import (
    BackgroundJob,
    ExtractLinksPayload,
    ExtractLinksResult,
    GenerateSelectorResult,
    GenerateSearchParamsResult,
    JobStatus,
    ProcessProjectEntriesPayload,
    ProcessProjectEntriesResult,
    TaskName,
    UpdateBackgroundJob,
    get_background_job,
)
from db.links import (
    CreateLink,
    Link,
    LinkStatus,
    UpdateLink,
    create_links,
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
from db.global_templates import list_all_global_templates
from providers.index import (
    ChatCompletionErrorResponse,
    ChatCompletionRequest,
    ResponseSchema,
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
from providers.index import providers
from logging_config import get_logger
from services.templates import create_messages_from_template

logger = get_logger(__name__)


async def generate_selector(job: BackgroundJob, project: Project):
    if not project.source_url:
        raise ValueError("Project must have a source URL")

    if not project.search_params:
        raise ValueError("Project must have search params")

    scraper = Scraper()
    logger.info(f"[{job.id}] Scraping content from {project.source_url}")
    content = await scraper.get_content(project.source_url, clean=True, pretty=True)
    provider = providers[project.ai_provider_config.api_provider]
    logger.info(f"[{job.id}] Generating selector with {provider.__class__.__name__}")

    global_templates = await list_all_global_templates()
    globals_dict = {gt.name: gt.content for gt in global_templates}
    context = {
        "content": content,
        "project": project.model_dump(),
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
        raise Exception(f"Failed to generate selector: {response.raw_response}")

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
    update_payload = UpdateProject(
        link_extraction_selector=selector_response.selectors,
        link_extraction_pagination_selector=selector_response.pagination_selector,
    )
    if project.status == ProjectStatus.search_params_generated:
        update_payload.status = ProjectStatus.selector_generated
    await update_project(project.id, update_payload)

    logger.info(f"[{job.id}] Starting crawl based on generated selectors.")

    await update_job_with_notification(
        job.id,
        UpdateBackgroundJob(
            total_items=project.max_pages_to_crawl,
            processed_items=0,
            progress=0,
        ),
    )

    current_url: str | None = project.source_url
    found_links_set = set()
    visited_content_hashes = set()
    pages_crawled = 0

    while current_url and pages_crawled < project.max_pages_to_crawl:
        pages_crawled += 1
        logger.info(f"[{job.id}] Crawling page {pages_crawled}: {current_url}")

        try:
            html = await scraper.get_content(current_url, clean=True)
            markdown = html_to_markdown(html)
        except Exception as e:
            logger.error(f"Failed to fetch {current_url}: {e}")
            break

        content_hash = hashlib.md5(markdown.encode()).hexdigest()
        if content_hash in visited_content_hashes:
            logger.info(f"[{job.id}] Duplicate page content detected. Ending crawl.")
            break
        visited_content_hashes.add(content_hash)

        soup = BeautifulSoup(html, "html.parser")

        # Extract content links
        for selector in selector_response.selectors:
            for link in soup.select(selector):
                if href := link.get("href"):
                    absolute_url = urljoin(str(current_url), href)  # pyright: ignore[reportArgumentType]
                    found_links_set.add(absolute_url)

        # Update job progress in real-time
        progress = (pages_crawled / project.max_pages_to_crawl) * 100
        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                processed_items=pages_crawled,
                progress=progress,
            ),
        )

        # Find next page link
        next_page_url = None
        if selector_response.pagination_selector:
            if next_page_element := soup.select_one(
                selector_response.pagination_selector
            ):
                if href := next_page_element.get("href"):
                    next_page_url = urljoin(str(current_url), href)  # pyright: ignore[reportArgumentType]

        if next_page_url == current_url:
            break
        current_url = next_page_url

    await update_job_with_notification(
        job.id,
        UpdateBackgroundJob(
            status=JobStatus.completed,
            progress=100,
            processed_items=pages_crawled,
            result=GenerateSelectorResult(
                found_urls=sorted(list(found_links_set)),
                pagination_selector=selector_response.pagination_selector,
                selectors=selector_response.selectors,
            ),
        ),
    )


async def generate_search_params(job: BackgroundJob, project: Project):
    if not project.prompt:
        raise ValueError("Project must have a prompt")

    provider = providers[project.ai_provider_config.api_provider]
    logger.info(
        f"[{job.id}] Generating search params with {provider.__class__.__name__}"
    )

    global_templates = await list_all_global_templates()
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
        raise Exception(f"Failed to generate search_params: {response.raw_response}")

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
    await update_project(project.id, update_payload)
    await update_job_with_notification(
        job.id,
        UpdateBackgroundJob(
            status=JobStatus.completed,
            result=GenerateSearchParamsResult(),
        ),
    )


async def extract_links(job: BackgroundJob, project: Project):
    if not project.source_url:
        raise ValueError("Project must have a source URL")

    if not isinstance(job.payload, ExtractLinksPayload):
        raise Exception("Invalid payload for extract_links task")

    if not project.link_extraction_selector:
        raise Exception("Project has no link_extraction_selector")

    if not job.payload.urls:
        logger.warning(f"[{job.id}] Extract links job received no URLs to save.")
        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.completed,
                result=ExtractLinksResult(links_found=0),
            ),
        )
        return

    links_to_create = [
        CreateLink(project_id=project.id, url=url) for url in job.payload.urls
    ]

    links = await create_links(links_to_create)
    await send_links_created_notification(job, links)
    if project.status == ProjectStatus.selector_generated:
        await update_project(
            project.id, UpdateProject(status=ProjectStatus.links_extracted)
        )
    await update_job_with_notification(
        job.id,
        UpdateBackgroundJob(
            status=JobStatus.completed,
            result=ExtractLinksResult(links_found=len(links_to_create)),
        ),
    )


async def _process_single_link(
    job: BackgroundJob, project: Project, link: Link, scraper: Scraper
) -> None:
    """Helper function to process a single link."""
    try:
        await update_link(link.id, UpdateLink(status=LinkStatus.processing))
        await send_link_updated_notification(job, link)
        content = (
            link.raw_content
            if link.raw_content
            else await scraper.get_content(link.url, type="markdown", clean=True)
        )
        provider = providers[project.ai_provider_config.api_provider]

        global_templates = await list_all_global_templates()
        globals_dict = {gt.name: gt.content for gt in global_templates}
        context = {
            "project": project.model_dump(),
            "content": content,
            "source_url": link.url,
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
            raise Exception(f"Failed to generate entry: {response.raw_response}")

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

        entry_response = LorebookEntryResponse.model_validate(response.content)
        created_entry = await create_lorebook_entry(
            CreateLorebookEntry(
                project_id=project.id,
                title=entry_response.title,
                content=entry_response.content,
                keywords=entry_response.keywords,
                source_url=link.url,
            )
        )
        await update_link(
            link.id,
            UpdateLink(
                status=LinkStatus.completed,
                lorebook_entry_id=created_entry.id,
                raw_content=content,
            ),
        )
        await send_link_updated_notification(job, link)
        await send_entry_created_notification(job, created_entry)

    except Exception as e:
        logger.error(f"[{job.id}] Error processing link {link.id}: {e}", exc_info=True)
        await update_link(
            link.id, UpdateLink(status=LinkStatus.failed, error_message=str(e))
        )
        await send_link_updated_notification(job, link)


async def process_project_entries(job: BackgroundJob, project: Project):
    """Process all pending links for a project to generate lorebook entries."""
    if not isinstance(job.payload, ProcessProjectEntriesPayload):
        raise Exception("Invalid payload for process_project_entries task")

    scraper = Scraper()
    pending_links = await get_processable_links_for_project(project.id)
    total_links = len(pending_links)
    if not total_links:
        raise Exception("No pending links found for project")

    processed_count = 0
    failed_count = 0

    if project.status == ProjectStatus.links_extracted:
        await update_project(project.id, UpdateProject(status=ProjectStatus.processing))
    await update_job_with_notification(
        job.id,
        UpdateBackgroundJob(total_items=total_links, processed_items=0, progress=0.0),
    )

    cancellation_event = asyncio.Event()

    async def poll_for_cancellation():
        while not cancellation_event.is_set():
            try:
                current_job = await get_background_job(job.id)
                if current_job and current_job.status == JobStatus.cancelling:
                    logger.info(f"[{job.id}] Cancellation requested, stopping job.")
                    cancellation_event.set()
                    break
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{job.id}] Error in cancellation poller: {e}")
                await asyncio.sleep(5)

    polling_task = asyncio.create_task(poll_for_cancellation())

    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)

    async def process_with_semaphore(link: Link):
        if cancellation_event.is_set():
            return

        async with semaphore:
            if cancellation_event.is_set():
                return

            await wait_for_rate_limit(project.id, project.requests_per_minute)

            if cancellation_event.is_set():
                return

            await _process_single_link(job, project, link, scraper)
            nonlocal processed_count, failed_count
            processed_count += 1
            updated_link = await get_link(link.id)
            if updated_link and updated_link.status == LinkStatus.failed:
                failed_count += 1
            progress = (processed_count / total_links) * 100
            await update_job_with_notification(
                job.id,
                UpdateBackgroundJob(
                    processed_items=processed_count,
                    progress=progress,
                ),
            )

    tasks = [process_with_semaphore(link) for link in pending_links]
    await asyncio.gather(*tasks)

    polling_task.cancel()

    if cancellation_event.is_set():
        await update_job_with_notification(
            job.id, UpdateBackgroundJob(status=JobStatus.canceled)
        )
        return

    final_project_status = (
        ProjectStatus.completed if failed_count == 0 else ProjectStatus.failed
    )
    await update_project(project.id, UpdateProject(status=final_project_status))
    await update_job_with_notification(
        job.id,
        UpdateBackgroundJob(
            status=JobStatus.completed,
            result=ProcessProjectEntriesResult(
                entries_created=processed_count - failed_count,
                entries_failed=failed_count,
            ),
        ),
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
        elif job.task_name == TaskName.EXTRACT_LINKS:
            await extract_links(job, project)
        elif job.task_name == TaskName.PROCESS_PROJECT_ENTRIES:
            await process_project_entries(job, project)
        elif job.task_name == TaskName.GENERATE_SEARCH_PARAMS:
            await generate_search_params(job, project)
    except Exception as e:
        logger.error(f"[{job.id}] Error processing job: {e}", exc_info=True)
        await update_job_with_notification(
            job.id,
            UpdateBackgroundJob(
                status=JobStatus.failed,
                error_message=str(e),
            ),
        )

import asyncio
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
    get_pending_links_for_project,
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
from services.scraper import Scraper
from providers.index import providers
from logging_config import get_logger
from services.templates import create_messages_from_template

logger = get_logger(__name__)


async def generate_selector(job: BackgroundJob, project: Project):
    if not project.source_url:
        raise ValueError("Project must have a source URL")

    if not project.search_params:
        raise ValueError("Project must have search params")

    """Generate a CSS selector for a project."""
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
    selector_urls = {}
    soup = BeautifulSoup(content, "html.parser")
    for selector in selector_response.selectors:
        links = soup.select(selector)
        urls: list[str] = [link.get("href") for link in links if link.get("href")]  # pyright: ignore[reportAssignmentType]
        # if URL is not absolute, join with source URL
        urls = [urljoin(project.source_url, url) for url in urls]
        selector_urls[selector] = urls

    await update_project(
        project.id,
        UpdateProject(
            link_extraction_selector=selector_response.selectors,
            status=ProjectStatus.selector_generated,
        ),
    )
    await update_job_with_notification(
        job.id,
        UpdateBackgroundJob(
            status=JobStatus.completed,
            result=GenerateSelectorResult(selectors=selector_urls),
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
    await update_project(
        project.id,
        UpdateProject(
            search_params=SearchParams(
                purpose=search_params_response.purpose,
                extraction_notes=search_params_response.extraction_notes,
                criteria=search_params_response.criteria,
            ),
            status=ProjectStatus.search_params_generated,
        ),
    )
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

    """Extract links from a project's source URL."""
    if not isinstance(job.payload, ExtractLinksPayload):
        raise Exception("Invalid payload for extract_links task")

    if not project.link_extraction_selector:
        raise Exception("Project has no link_extraction_selector")

    links_to_create = []
    for url in job.payload.urls:
        absolute_url = urljoin(project.source_url, url)
        links_to_create.append(CreateLink(project_id=project.id, url=absolute_url))

    links = await create_links(links_to_create)
    await send_links_created_notification(job, links)
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
    pending_links = await get_pending_links_for_project(project.id)
    total_links = len(pending_links)
    if not total_links:
        raise Exception("No pending links found for project")

    processed_count = 0
    failed_count = 0

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

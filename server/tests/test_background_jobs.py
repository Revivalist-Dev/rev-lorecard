import pytest
import pytest_asyncio
from psycopg_pool import AsyncConnectionPool
from litestar.testing import AsyncTestClient

from db.projects import (
    AiProviderConfig,
    CreateProject,
    ProjectTemplates,
)
from services.background_jobs import process_background_job


@pytest_asyncio.fixture(autouse=True)
async def cleanup_tables(db_connection_pool: AsyncConnectionPool):
    """Fixture to clean up tables after each test."""
    yield
    async with db_connection_pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                'TRUNCATE "Project", "BackgroundJob", "ApiRequestLog", "Link", "LorebookEntry", "GlobalTemplate" CASCADE;'
            )


@pytest.fixture
def real_project_payload() -> CreateProject:
    """Fixture to return a project payload with real-world settings."""
    selector_prompt = "{{globals.selector_prompt}}"
    entry_creation_prompt = """{{globals.entry_creation_prompt}}"""
    search_params_prompt = "{{globals.search_params_prompt}}"

    return CreateProject(
        id="skyrim-locations-test",
        name="Skyrim Locations (Integration Test)",
        source_url="https://elderscrolls.fandom.com/wiki/Category:Skyrim:_Locations",
        prompt="Skyrim locations",
        templates=ProjectTemplates(
            selector_generation=selector_prompt,
            entry_creation=entry_creation_prompt,
            search_params_generation=search_params_prompt,
        ),
        ai_provider_config=AiProviderConfig(
            api_provider="openrouter",
            model_name="google/gemini-2.5-flash",
            model_parameters={"temperature": 0.7},
        ),
    )


@pytest.mark.asyncio
async def test_generate_selector_job_with_test_client(
    client_test: AsyncTestClient,
    real_project_payload: CreateProject,
):
    """
    End-to-end test for the GENERATE_SELECTOR job using the AsyncTestClient.
    """
    project_id = real_project_payload.id

    # 1. Create the project
    response = await client_test.post(
        "/api/projects", json=real_project_payload.model_dump()
    )
    assert response.status_code == 201

    # 2. Update the project for setting search_params
    response = await client_test.patch(
        f"/api/projects/{project_id}",
        json={
            "search_params": {
                "purpose": "To gather detailed character information including backgrounds, traits, and relationships",
                "extraction_notes": "Focus extraction on the specific type of content requested. For characters: extract names, aliases, descriptions, personality, history, and relationships. For locations: extract features, history, significance. For other topics: extract key aspects relevant to the subject.",
                "criteria": "Page must be specifically created as a character article (e.g., character profile, biography page). Reject pages that only mention or reference the character within other content.",
            }
        },
    )
    assert response.status_code == 200

    # 3. Start the 'generate_selector' job
    response = await client_test.post(
        "/api/jobs/generate-selector", json={"project_id": project_id}
    )
    assert response.status_code == 201
    job_id = response.json()["data"]["id"]

    # 4. Run the worker to process the job
    # The worker will pick up the pending job and execute it.
    await process_background_job(job_id)

    # 5. Check the job status via the API
    response = await client_test.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    job_data = response.json()["data"]
    assert job_data["status"] == "completed"

    # 6. Verify the project was updated
    response = await client_test.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    project_data = response.json()["data"]
    assert project_data["status"] == "selector_generated"
    assert project_data["link_extraction_selector"] is not None
    assert len(project_data["link_extraction_selector"]) > 0

    # 7. Verify the API log was created
    response = await client_test.get(f"/api/projects/{project_id}/logs")
    assert response.status_code == 200
    logs_data = response.json()
    assert logs_data["meta"]["total_items"] == 1
    assert logs_data["data"][0]["error"] is False
    assert logs_data["data"][0]["job_id"] == job_id


@pytest.mark.asyncio
async def test_generate_search_params_job_with_test_client(
    client_test: AsyncTestClient,
    real_project_payload: CreateProject,
):
    """
    End-to-end test for the GENERATE_SEARCH_PARAMS job using the AsyncTestClient.
    """
    project_id = real_project_payload.id

    # 1. Create the project
    response = await client_test.post(
        "/api/projects", json=real_project_payload.model_dump()
    )
    assert response.status_code == 201

    # 2. Start the 'generate_search_params' job
    response = await client_test.post(
        "/api/jobs/generate-search-params", json={"project_id": project_id}
    )
    assert response.status_code == 201
    job_id = response.json()["data"]["id"]

    # 3. Run the worker to process the job
    await process_background_job(job_id)

    # 4. Check the job status via the API
    response = await client_test.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    job_data = response.json()["data"]
    assert job_data["status"] == "completed"

    # 5. Verify the project was updated
    response = await client_test.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    project_data = response.json()["data"]
    assert project_data["search_params"] is not None
    assert "purpose" in project_data["search_params"]
    assert "extraction_notes" in project_data["search_params"]
    assert "criteria" in project_data["search_params"]

    # 6. Verify the API log was created
    response = await client_test.get(f"/api/projects/{project_id}/logs")
    assert response.status_code == 200
    logs_data = response.json()
    assert logs_data["meta"]["total_items"] == 1
    assert logs_data["data"][0]["error"] is False
    assert logs_data["data"][0]["job_id"] == job_id


@pytest.mark.asyncio
async def test_extract_links_job_with_test_client(
    client_test: AsyncTestClient,
    real_project_payload: CreateProject,
):
    """
    End-to-end test for the EXTRACT_LINKS job using the AsyncTestClient.
    """
    project_id = real_project_payload.id
    test_links = [
        "https://elderscrolls.fandom.com/wiki/A_Bandit%27s_Book",
        "https://elderscrolls.fandom.com/wiki/A_Bloody_Trail",
        "https://elderscrolls.fandom.com/wiki/Abandoned_House_(Markarth)",
    ]

    # 1. Create the project
    response = await client_test.post(
        "/api/projects", json=real_project_payload.model_dump()
    )
    assert response.status_code == 201

    # 2. Manually set the link_extraction_selector for the project
    response = await client_test.patch(
        f"/api/projects/{project_id}",
        json={"link_extraction_selector": ["a.category-page__member-link"]},
    )
    assert response.status_code == 200

    # 3. Start the 'extract_links' job
    response = await client_test.post(
        "/api/jobs/extract-links",
        json={"project_id": project_id, "urls": test_links},
    )
    assert response.status_code == 201
    job_id = response.json()["data"]["id"]

    # 4. Run the worker to process the job
    await process_background_job(job_id)

    # 5. Check the job status via the API
    response = await client_test.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    job_data = response.json()["data"]
    assert job_data["status"] == "completed"
    assert job_data["result"]["links_found"] == len(test_links)

    # 6. Verify the project was updated
    response = await client_test.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    project_data = response.json()["data"]
    assert project_data["status"] == "links_extracted"

    # 7. Verify the links were created
    response = await client_test.get(f"/api/projects/{project_id}/links")
    assert response.status_code == 200
    links_data = response.json()
    assert links_data["meta"]["total_items"] == len(test_links)
    # Check if one of the URLs is in the created links
    assert any(
        link["url"] == "https://elderscrolls.fandom.com/wiki/A_Bandit%27s_Book"
        for link in links_data["data"]
    )


@pytest.mark.asyncio
async def test_process_project_entries_job_with_test_client(
    client_test: AsyncTestClient,
    real_project_payload: CreateProject,
):
    """
    End-to-end test for the PROCESS_PROJECT_ENTRIES job using the AsyncTestClient.
    """
    project_id = real_project_payload.id
    test_links = [
        "https://elderscrolls.fandom.com/wiki/A_Bandit%27s_Book",
        "https://elderscrolls.fandom.com/wiki/A_Bloody_Trail",
        "https://elderscrolls.fandom.com/wiki/Abandoned_House_(Markarth)",
    ]

    # 1. Create the project
    response = await client_test.post(
        "/api/projects", json=real_project_payload.model_dump()
    )
    assert response.status_code == 201

    # 2. Manually set the link_extraction_selector for the project to simulate link extraction
    response = await client_test.patch(
        f"/api/projects/{project_id}",
        json={"link_extraction_selector": ["a.category-page__member-link"]},
    )
    assert response.status_code == 200

    # 3. Create links by calling the extract-links job first
    response = await client_test.post(
        "/api/jobs/extract-links",
        json={"project_id": project_id, "urls": test_links},
    )
    assert response.status_code == 201
    extract_links_job_id = response.json()["data"]["id"]
    await process_background_job(extract_links_job_id)

    # Verify links were created
    response = await client_test.get(f"/api/projects/{project_id}/links")
    assert response.json()["meta"]["total_items"] == len(test_links)

    # 4. Start the 'process-project-entries' job
    response = await client_test.post(
        "/api/jobs/process-project-entries", json={"project_id": project_id}
    )
    assert response.status_code == 201
    process_entries_job_id = response.json()["data"]["id"]

    # 5. Run the worker to process the job
    await process_background_job(process_entries_job_id)

    # 6. Check the job status via the API
    response = await client_test.get(f"/api/jobs/{process_entries_job_id}")
    assert response.status_code == 200
    job_data = response.json()["data"]
    assert job_data["status"] == "completed"
    assert job_data["result"]["entries_created"] == len(test_links)
    assert job_data["result"]["entries_failed"] == 0

    # 7. Verify the project was updated
    response = await client_test.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    project_data = response.json()["data"]
    assert project_data["status"] == "completed"

    # 8. Verify the lorebook entries were created and have content
    response = await client_test.get(f"/api/projects/{project_id}/entries")
    assert response.status_code == 200
    entries_data = response.json()
    assert entries_data["meta"]["total_items"] == len(test_links)
    for entry in entries_data["data"]:
        assert entry["content"] is not None
        assert len(entry["content"]) > 0

    # 9. Verify the API logs were created
    response = await client_test.get(f"/api/projects/{project_id}/logs")
    assert response.status_code == 200
    logs_data = response.json()
    # One for each link
    assert logs_data["meta"]["total_items"] == len(test_links)
    assert all(log["error"] is False for log in logs_data["data"])

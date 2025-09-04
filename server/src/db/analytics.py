from typing import Dict
from pydantic import BaseModel
from db.connection import get_db_connection
from db.links import LinkStatus
from db.background_jobs import JobStatus


class ProjectAnalytics(BaseModel):
    """Aggregated analytics for a project."""

    total_requests: int
    total_cost: float
    has_unknown_costs: bool
    total_input_tokens: int
    total_output_tokens: int
    average_latency_ms: float
    link_status_counts: Dict[LinkStatus, int]
    job_status_counts: Dict[JobStatus, int]
    total_lorebook_entries: int
    total_links: int
    total_jobs: int


async def get_project_analytics(project_id: str) -> ProjectAnalytics | None:
    """Retrieve aggregated analytics for a specific project."""
    db = await get_db_connection()
    api_query = """
        SELECT
            COUNT(*) AS total_requests,
            SUM(CASE WHEN calculated_cost >= 0 THEN calculated_cost ELSE 0 END) AS total_cost,
            SUM(input_tokens) AS total_input_tokens,
            SUM(output_tokens) AS total_output_tokens,
            AVG(latency_ms) AS average_latency_ms,
            MAX(CASE WHEN calculated_cost < 0 THEN 1 ELSE 0 END) as has_unknown_costs
        FROM "ApiRequestLog"
        WHERE project_id = %s
    """
    api_result = await db.fetch_one(api_query, (project_id,))

    link_query = """
        SELECT status, COUNT(*) as count
        FROM "Link"
        WHERE project_id = %s
        GROUP BY status
    """
    link_results = await db.fetch_all(link_query, (project_id,))

    link_status_counts = {status: 0 for status in LinkStatus}
    if link_results:
        for row in link_results:
            link_status_counts[LinkStatus(row["status"])] = row["count"]
    total_links = sum(link_status_counts.values())

    job_query = """
        SELECT status, COUNT(*) as count
        FROM "BackgroundJob"
        WHERE project_id = %s
        GROUP BY status
    """
    job_results = await db.fetch_all(job_query, (project_id,))

    job_status_counts = {status: 0 for status in JobStatus}
    if job_results:
        for row in job_results:
            job_status_counts[JobStatus(row["status"])] = row["count"]
    total_jobs = sum(job_status_counts.values())

    entry_query = 'SELECT COUNT(*) as count FROM "LorebookEntry" WHERE project_id = %s'
    entry_result = await db.fetch_one(entry_query, (project_id,))
    total_lorebook_entries = entry_result["count"] if entry_result else 0

    if not api_result or api_result["total_requests"] == 0:
        return ProjectAnalytics(
            total_requests=0,
            total_cost=0.0,
            has_unknown_costs=False,
            total_input_tokens=0,
            total_output_tokens=0,
            average_latency_ms=0.0,
            link_status_counts=link_status_counts,
            job_status_counts=job_status_counts,
            total_lorebook_entries=total_lorebook_entries,
            total_links=total_links,
            total_jobs=total_jobs,
        )

    # Ensure values are not None before creating the model
    return ProjectAnalytics(
        total_requests=api_result.get("total_requests") or 0,
        total_cost=float(api_result.get("total_cost") or 0.0),
        has_unknown_costs=bool(api_result.get("has_unknown_costs")),
        total_input_tokens=api_result.get("total_input_tokens") or 0,
        total_output_tokens=api_result.get("total_output_tokens") or 0,
        average_latency_ms=float(api_result.get("average_latency_ms") or 0.0),
        link_status_counts=link_status_counts,
        job_status_counts=job_status_counts,
        total_lorebook_entries=total_lorebook_entries,
        total_links=total_links,
        total_jobs=total_jobs,
    )

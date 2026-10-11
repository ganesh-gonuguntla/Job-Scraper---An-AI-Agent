import logging
from typing import Any, Dict
from backend.schemas import SearchQuery, RawResult, Job
from backend.search import search_query

logger = logging.getLogger(__name__)

def job_to_raw_result(j: Job, query_str: str) -> RawResult:
    return RawResult(
        url=j.apply_url or j.url,
        title=f"{j.title} at {j.company}",
        text=f"Company: {j.company}\nLocation: {j.location}\nRemote: {j.remote}\nDescription: {j.description or ''}\nSkills: {', '.join(j.skills_required)}",
        published=j.posted_date,
        source_query=query_str,
        rule_score=0.0,
        job=j,
    )

async def search_one(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parallel worker for a single search query.
    Queries real job sources (Adzuna, JSearch, Remotive, Arbeitnow, Greenhouse),
    packages real Job metadata into RawResult, and appends to raw_results via reducer.
    """
    raw_query = state.get("query")
    if isinstance(raw_query, dict):
        query = SearchQuery.model_validate(raw_query)
    elif isinstance(raw_query, SearchQuery):
        query = raw_query
    else:
        return {"raw_results": [], "errors": ["Invalid query payload"]}

    max_age_days = state.get("max_age_days", 30)
    preferences = state.get("preferences")

    try:
        res = await search_query(query, preferences=preferences, max_age_days=max_age_days)
        real_jobs = res[0] if isinstance(res, tuple) else res
        raw_items = [job_to_raw_result(j, query.q) for j in real_jobs]
        return {
            "raw_results": raw_items,
            "errors": [],
        }
    except Exception as e:
        logger.error(f"Error in search_one for query '{query.q}': {e}")
        return {
            "raw_results": [],
            "errors": [f"Search error for '{query.q}': {str(e)}"],
        }

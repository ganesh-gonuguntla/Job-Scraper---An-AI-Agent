import logging
from typing import Any, Dict
from backend.search import search_query
from backend.schemas import SearchQuery

logger = logging.getLogger(__name__)

async def search_one(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parallel worker for a single search query.
    Appends discovered RawResult items to raw_results via reducer.
    Non-fatal errors append to errors.
    """
    raw_query = state.get("query")
    if isinstance(raw_query, dict):
        query = SearchQuery.model_validate(raw_query)
    elif isinstance(raw_query, SearchQuery):
        query = raw_query
    else:
        return {"raw_results": [], "errors": ["Invalid query payload"]}

    max_age_days = state.get("max_age_days", 30)

    try:
        results = await search_query(query, max_age_days=max_age_days)
        return {
            "raw_results": results,
            "errors": [],
        }
    except Exception as e:
        logger.error(f"Error in search_one for query '{query.q}': {e}")
        return {
            "raw_results": [],
            "errors": [f"Search error for '{query.q}': {str(e)}"],
        }

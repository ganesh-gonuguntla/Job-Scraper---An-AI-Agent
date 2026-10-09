from typing import Any, Dict, List
from langgraph.types import Send
from backend.state import GraphState

def search_dispatcher(state: GraphState) -> Dict[str, Any]:
    """
    Search dispatcher node preparing queries for parallel fan-out.
    """
    return {
        "status_note": f"Searching across {len(state.get('queries', []))} query angles..."
    }

def dispatch_search_queries(state: GraphState) -> List[Send]:
    """
    Conditional edge returning Send('search_one', payload) for each query in parallel.
    """
    queries = state.get("queries", [])
    prefs = state.get("preferences")
    max_age_days = getattr(prefs, "max_age_days", 30)

    sends = []
    for q in queries:
        sends.append(Send("search_one", {
            "query": q,
            "max_age_days": max_age_days,
        }))
    return sends

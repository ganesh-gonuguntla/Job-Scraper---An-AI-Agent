from typing import Any, Dict
from langgraph.types import interrupt
from backend.schemas import Profile, SearchQuery
from backend.state import GraphState

def human_review(state: GraphState) -> Dict[str, Any]:
    """
    Pauses execution using LangGraph interrupt.
    The UI renders editable skills, titles, and queries.
    When resumed with edited values via Command(resume=...),
    they overwrite the corresponding state attributes.
    """
    profile = state.get("profile")
    queries = state.get("queries", [])

    profile_dict = profile.model_dump() if hasattr(profile, "model_dump") else profile
    queries_dict = [q.model_dump() if hasattr(q, "model_dump") else q for q in queries]

    # Trigger interrupt with current proposal
    user_edits = interrupt({
        "profile": profile_dict,
        "queries": queries_dict,
    })

    updates: Dict[str, Any] = {}

    if isinstance(user_edits, dict):
        if "profile" in user_edits and user_edits["profile"]:
            try:
                updates["profile"] = Profile.model_validate(user_edits["profile"])
            except Exception:
                pass
        if "queries" in user_edits and user_edits["queries"]:
            try:
                updates["queries"] = [
                    SearchQuery.model_validate(q) for q in user_edits["queries"]
                ]
            except Exception:
                pass

    return updates

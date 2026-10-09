import json
import logging
from typing import Any, Dict
from backend.llm import invoke_structured
from backend.schemas import RefinerOutput, Profile
from backend.state import GraphState

logger = logging.getLogger(__name__)

QUERY_REFINER_SYSTEM_PROMPT = """Previous job-search queries underperformed. Do NOT repeat them.
Input: compact profile, the failed queries with result counts, and the
dominant failure reasons (too_few_results / wrong_job_type / low_skill_overlap /
stale). Diagnose in one sentence, then write up to 4 NEW queries that broaden
the title, drop restrictive terms, or switch boards. Max 12 words each. JSON only."""

async def query_refiner(state: GraphState) -> Dict[str, Any]:
    profile: Profile | None = state.get("profile")
    current_queries = state.get("queries", [])
    retry_count = state.get("retry_count", 0)

    compact_profile = {
        "seniority": profile.seniority if profile else "mid",
        "top_skills": profile.top_skills if profile else [],
        "target_titles": profile.target_titles if profile else [],
    }

    failed_queries_info = [
        {"q": q.q, "angle": q.angle, "site": q.site}
        for q in current_queries
    ]

    user_prompt = (
        f"PROFILE: {json.dumps(compact_profile)}\n"
        f"FAILED_QUERIES: {json.dumps(failed_queries_info)}\n"
        f"FAILURE_REASON: too_few_results or low_skill_overlap"
    )

    result = await invoke_structured(
        schema=RefinerOutput,
        system_prompt=QUERY_REFINER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        preferred_provider="gemini",
        max_tokens=600,
        fixture_key="refiner_output"
    )

    new_queries = result.queries if result and result.queries else current_queries
    diagnosis = result.diagnosis if result and result.diagnosis else "Refining search terms."

    return {
        "queries": new_queries,
        "retry_count": retry_count + 1,
        "status_note": f"Retry {retry_count + 1}: {diagnosis}",
    }

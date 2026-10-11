import json
import logging
from typing import Any, Dict, List

from backend.config import DEFAULT_COUNTRIES
from backend.llm import invoke_structured
from backend.schemas import RefinerOutput, Profile, SearchQuery
from backend.state import GraphState

logger = logging.getLogger(__name__)

QUERY_REFINER_SYSTEM_PROMPT = """You are an automated Search Expansion Agent for structured job board APIs.
Previous queries produced fewer than 15 jobs. We need to expand the search.

RULES:
1. STRICTLY NO WEB SEARCH LEFTOVERS: NO 'site:' operators, NO filler words ('jobs', 'hiring', 'openings', 'fte', 'careers').
2. BROADEN TITLES: Add adjacent role titles, entry-level variants, and internship variants.
   For Data Analyst: 'Junior Data Analyst', 'Business Analyst', 'BI Analyst', 'Power BI Developer', 'Data Analyst Intern'.
   For Full Stack: 'Junior Software Engineer', 'Frontend Developer', 'Backend Developer', 'Full Stack Intern'.
3. LOCATION & COUNTRIES:
   Drop narrow city constraints. Distribute across countries ('in', 'us', 'gb'). Set remote: true for remote roles.

Return valid JSON with 'diagnosis' and up to 6 'new_queries'."""

def synthesize_fallback_expansion(profile: Profile | None, round_num: int) -> List[SearchQuery]:
    skills = profile.top_skills if profile else ["python", "sql"]
    is_data = any(s in skills for s in ["sql", "power bi", "tableau", "excel", "data analysis"])

    if is_data:
        titles = [
            ("Business Analyst", "in", False, "adjacent_title", "any"),
            ("BI Developer", "in", False, "adjacent_title", "any"),
            ("Junior Data Analyst", "in", False, "entry_level", "fulltime"),
            ("Data Analyst Intern", "in", False, "internship", "intern"),
            ("Data Analyst", "us", True, "exact_title", "any"),
            ("Reporting Analyst", "gb", False, "adjacent_title", "any"),
        ]
    else:
        titles = [
            ("Frontend Developer", "in", False, "adjacent_title", "any"),
            ("Backend Developer", "in", False, "adjacent_title", "any"),
            ("Junior Software Engineer", "in", False, "entry_level", "fulltime"),
            ("Software Engineer Intern", "in", False, "internship", "intern"),
            ("Full Stack Developer", "us", True, "exact_title", "any"),
            ("Web Developer", "gb", False, "adjacent_title", "any"),
        ]

    queries = []
    for title, country, remote_flag, angle, emp_type in titles:
        queries.append(SearchQuery(
            title_keywords=title,
            skills=skills[:2],
            location=None,
            country=country,
            remote=remote_flag,
            employment_type=emp_type,
            date_posted="month",
            angle=angle,
        ))
    return queries

async def query_refiner(state: GraphState) -> Dict[str, Any]:
    profile: Profile | None = state.get("profile")
    current_queries = state.get("queries", [])
    retry_count = state.get("retry_count", 0)
    round_num = retry_count + 1

    compact_profile = {
        "seniority": profile.seniority if profile else "mid",
        "top_skills": profile.top_skills if profile else [],
        "target_titles": profile.target_titles if profile else [],
    }

    user_prompt = (
        f"PROFILE: {json.dumps(compact_profile)}\n"
        f"EXPANSION_ROUND: {round_num}\n"
        f"TARGET: Produce 6 broadened API queries covering adjacent titles, entry-level, internship, and countries in, us, gb."
    )

    result = await invoke_structured(
        schema=RefinerOutput,
        system_prompt=QUERY_REFINER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        role="research",
        max_tokens=1500,
    )

    new_queries = result.queries if result and result.queries else []
    if len(new_queries) < 4:
        new_queries = synthesize_fallback_expansion(profile, round_num)

    diagnosis = result.diagnosis if result and result.diagnosis else f"Expansion round {round_num}: broadened titles and countries"

    return {
        "queries": new_queries,
        "retry_count": retry_count + 1,
        "status_note": f"Quality Gate Expansion (Round {round_num}/2): {diagnosis}",
    }

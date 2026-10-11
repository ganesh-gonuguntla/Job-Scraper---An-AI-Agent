from typing import Any, Dict, List
from backend.schemas import ScoredJob, Preferences
from backend.state import GraphState

def apply_ranker(scored_jobs: List[ScoredJob], preferences: Preferences) -> List[ScoredJob]:
    """
    Deterministic ranking with soft preference boosts (NEVER drops):
    - Job type, location, and salary are soft ranking boosts (+5 pts each), never filters.
    - All jobs scoring >= 20 are shown.
    - Sorting by user preference: match, salary, or recency.
    """
    allowed_types = set(t.lower() for t in (preferences.job_types or ["fte", "intern"]))
    target_locations = [loc.lower().strip() for loc in (preferences.locations or ["any"])]
    is_any_loc = any(loc in ["any", "worldwide", "global", "all"] for loc in target_locations)
    min_sal = preferences.min_salary_inr_annual

    # Calculate soft ranking boost per job without dropping any job
    job_boosted: List[tuple[ScoredJob, float]] = []
    for job in scored_jobs:
        boost = 0.0

        # Soft boost 1: Job type alignment
        if job.job_type in allowed_types or (job.job_type == "unknown" and len(allowed_types) > 0):
            boost += 5.0

        # Soft boost 2: Location / Remote preference
        job_loc = (job.location or "").lower()
        if is_any_loc or job.remote:
            boost += 5.0
        elif any(loc in job_loc for loc in target_locations):
            boost += 5.0

        # Soft boost 3: Salary preference
        if min_sal is not None and job.salary_annual_inr is not None:
            if job.salary_annual_inr >= min_sal:
                boost += 5.0

        effective_score = job.score + boost
        job_boosted.append((job, effective_score))

    # Requirement: Everything scoring >= 20 is shown
    qualifying_pairs = [(j, eff) for (j, eff) in job_boosted if j.score >= 20]
    if not qualifying_pairs and job_boosted:
        # Fallback to show whatever was scored
        qualifying_pairs = job_boosted

    sort_by = preferences.sort_by or "match"

    def sort_key(pair: tuple[ScoredJob, float]):
        j, eff = pair
        score_val = eff
        recency_val = j.posted_date or ""
        sal_val = j.salary_annual_inr if j.salary_annual_inr is not None else -1.0

        if sort_by == "match":
            return (score_val, recency_val)
        elif sort_by == "salary":
            return (sal_val, score_val, recency_val)
        elif sort_by == "recency":
            return (recency_val, score_val)
        return (score_val, recency_val)

    qualifying_pairs.sort(key=sort_key, reverse=True)
    return [pair[0] for pair in qualifying_pairs]

def ranker(state: GraphState) -> Dict[str, Any]:
    scored_jobs = state.get("scored_jobs", [])
    prefs = state.get("preferences")
    if not prefs:
        prefs = Preferences(job_types=["fte", "intern"], sort_by="match")

    final_jobs = apply_ranker(scored_jobs, prefs)

    funnel = state.get("funnel", {})
    if funnel:
        funnel.setdefault("shown", {})["count"] = len(final_jobs)

    return {
        "final_jobs": final_jobs,
        "funnel": funnel,
        "status_note": f"Ranked {len(final_jobs)} jobs with soft preference boosts (score >= 20)",
    }

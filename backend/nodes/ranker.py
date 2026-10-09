from typing import Any, Dict, List
from backend.schemas import ScoredJob, Preferences
from backend.state import GraphState

def apply_ranker(scored_jobs: List[ScoredJob], preferences: Preferences) -> List[ScoredJob]:
    """
    Deterministic ranking and filtering:
    1. Filter by allowed job types (if known).
    2. Filter by min_salary_inr_annual: drop if salary is listed and max < min_salary.
       (Unlisted salary is kept).
    3. Sort according to preferences.sort_by:
       - 'match': score descending, then recency descending
       - 'salary': salary_annual_inr descending (nulls last), then score descending
       - 'recency': posted_date descending (nulls last), then score descending
    4. Cap at top 15.
    """
    filtered = []
    allowed_types = set(preferences.job_types)
    min_sal = preferences.min_salary_inr_annual

    for job in scored_jobs:
        # Check job type: if known and not in allowed_types, drop
        if job.job_type != "unknown" and job.job_type not in allowed_types:
            continue

        # Check salary: if min_salary requested and job has known salary below it, drop
        if min_sal is not None and job.salary_annual_inr is not None:
            if job.salary_annual_inr < min_sal:
                continue

        filtered.append(job)

    # Sorting
    sort_by = preferences.sort_by

    def sort_key(j: ScoredJob):
        score_val = j.score
        recency_val = j.posted_date or ""
        sal_val = j.salary_annual_inr if j.salary_annual_inr is not None else -1.0

        if sort_by == "match":
            # Primary: score desc, Secondary: recency desc
            return (score_val, recency_val)
        elif sort_by == "salary":
            # Primary: salary desc (nulls last, so -1.0 is lowest), Secondary: score desc
            return (sal_val, score_val, recency_val)
        elif sort_by == "recency":
            # Primary: recency desc, Secondary: score desc
            return (recency_val, score_val)
        return (score_val, recency_val)

    filtered.sort(key=sort_key, reverse=True)
    return filtered[:15]

def ranker(state: GraphState) -> Dict[str, Any]:
    scored_jobs = state.get("scored_jobs", [])
    prefs = state.get("preferences")
    if not prefs:
        prefs = Preferences(job_types=["fte", "intern"], sort_by="match")

    final_jobs = apply_ranker(scored_jobs, prefs)
    return {
        "final_jobs": final_jobs,
        "status_note": f"Ranked top {len(final_jobs)} jobs according to preferences",
    }

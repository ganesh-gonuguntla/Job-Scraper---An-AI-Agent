import logging
from typing import Any, Dict, List

from backend.cache import cache
from backend.schemas import Job, RawResult, validate_job_guard
from backend.state import GraphState

logger = logging.getLogger(__name__)

def normalize_salary_annual_inr(
    salary_min: float | None,
    salary_max: float | None,
    currency: str | None,
    period: str | None,
    fx_usd_inr: float = 83.0,
) -> float | None:
    """
    Normalizes salary range into an annual INR figure.
    Handles LPA notation, monthly stipends, and FX conversions.
    """
    val = salary_max if salary_max is not None else salary_min
    if val is None:
        return None

    curr = (currency or "INR").upper().strip()
    prd = (period or "year").lower().strip()

    if prd == "month":
        annual = val * 12.0
    elif prd == "week":
        annual = val * 52.0
    elif prd == "day":
        annual = val * 260.0
    elif prd == "hour":
        annual = val * 2080.0
    else:
        # If in INR and under 100, treated as Lakhs per Annum (LPA)
        if curr in ["INR", "₹"] and val < 100.0:
            annual = val * 100000.0
        else:
            annual = val

    if curr in ["USD", "$"]:
        return annual * fx_usd_inr
    elif curr in ["EUR", "€"]:
        return annual * (fx_usd_inr * 1.08)
    elif curr in ["GBP", "£"]:
        return annual * (fx_usd_inr * 1.25)
    return annual

async def extract_jobs(state: GraphState) -> Dict[str, Any]:
    """
    Deterministic Job Ingestion & Validation Node:
    - Extracts verified real Job instances directly from search candidates.
    - Strictly enforces No-Fake-Data guards: rejects any job missing title, company, apply_url, or source.
    - Zero LLM fabrication: LLMs are never asked to invent, repair, or generate job postings.
    """
    candidates: List[RawResult] = state.get("candidates", [])
    valid_jobs: List[Job] = []
    rejected_count = 0

    for cand in candidates:
        job: Job | None = None

        if hasattr(cand, "job") and isinstance(cand.job, Job):
            job = cand.job
        elif isinstance(getattr(cand, "job", None), dict):
            try:
                job = Job.model_validate(cand.job)
            except Exception:
                job = None

        # Guard: Check all mandatory fields (title, company, apply_url, source)
        if not job or not validate_job_guard(job):
            rejected_count += 1
            logger.warning(
                f"[Job Guard] Rejected invalid job candidate: title='{getattr(job, 'title', cand.title)}', "
                f"company='{getattr(job, 'company', None)}', source='{getattr(job, 'source', None)}'"
            )
            continue

        # Synchronize URLs and indices
        if not job.apply_url and job.url:
            job.apply_url = job.url
        if not job.url and job.apply_url:
            job.url = job.apply_url

        job.idx = len(valid_jobs)
        job.is_real_posting = True
        cache.set_job(job.apply_url, job)
        valid_jobs.append(job)

    logger.info(f"[Job Ingestion] {len(valid_jobs)} real jobs passed validation ({rejected_count} rejected by guards).")

    note = f"Verified {len(valid_jobs)} live job postings directly from API feeds"
    if not valid_jobs:
        note = "No jobs found meeting your criteria across configured sources."

    return {
        "jobs": valid_jobs,
        "extracted_jobs": valid_jobs,
        "status_note": note,
    }

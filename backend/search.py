import asyncio
from datetime import datetime, timezone
import logging
import re
import time
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from backend.config import SOURCE_TIMEOUT_SECONDS
from backend.schemas import SearchQuery, Job, Preferences, validate_job_guard
from backend.sources.adzuna import search_adzuna
from backend.sources.jsearch import search_jsearch
from backend.sources.boards import search_remotive, search_arbeitnow, search_greenhouse

logger = logging.getLogger(__name__)

# Global tracker for latest run source statuses and counts
latest_source_statuses: Dict[str, Dict[str, Any]] = {
    "Adzuna": {"count": 0, "status": "ok", "reason": "Initialized", "elapsed_s": 0.0},
    "JSearch": {"count": 0, "status": "ok", "reason": "Initialized", "elapsed_s": 0.0},
    "Remotive": {"count": 0, "status": "ok", "reason": "Initialized", "elapsed_s": 0.0},
    "Arbeitnow": {"count": 0, "status": "ok", "reason": "Initialized", "elapsed_s": 0.0},
    "Greenhouse": {"count": 0, "status": "ok", "reason": "Initialized", "elapsed_s": 0.0},
    "deduped": {"count": 0, "status": "ok", "reason": "Initialized", "elapsed_s": 0.0},
}

latest_source_counts: Dict[str, int] = {
    "Adzuna": 0,
    "JSearch": 0,
    "Remotive": 0,
    "Arbeitnow": 0,
    "Greenhouse": 0,
    "deduped": 0,
}

def normalize_apply_url(raw_url: str) -> str:
    """
    Strips tracking queries (utm_*, ref, etc.) while preserving essential job IDs.
    """
    try:
        parsed = urlparse(raw_url.strip())
        qs = parse_qs(parsed.query)
        clean_qs = {k: v for k, v in qs.items() if not k.startswith("utm_") and k not in ["ref", "source", "refId"]}
        new_query = urlencode(clean_qs, doseq=True)
        return urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.params, new_query, ""))
    except Exception:
        return raw_url.strip()

def deduplicate_jobs(jobs: List[Job]) -> Tuple[List[Job], Dict[str, int]]:
    """
    Deduplicates real jobs across multiple sources by:
    1. Normalized apply URL
    2. Normalized (company, title) tuple
    """
    counts: Dict[str, int] = {"Adzuna": 0, "JSearch": 0, "Remotive": 0, "Arbeitnow": 0, "Greenhouse": 0, "deduped": 0}
    for j in jobs:
        src = j.source or "Other"
        counts[src] = counts.get(src, 0) + 1

    seen_urls = set()
    seen_company_titles = set()
    deduped: List[Job] = []

    for j in jobs:
        # Enforce No-Fake-Data Guard:
        if not validate_job_guard(j):
            logger.warning(f"[Guard Rejected] Job missing required fields: title={j.title}, company={j.company}, source={j.source}")
            continue

        norm_url = normalize_apply_url(j.apply_url or j.url)
        company_clean = re.sub(r"[^a-zA-Z0-9]", "", (j.company or "").lower())
        title_clean = re.sub(r"[^a-zA-Z0-9]", "", (j.title or "").lower())
        comp_title_key = (company_clean, title_clean[:25])

        if norm_url in seen_urls or (company_clean and comp_title_key in seen_company_titles):
            continue

        seen_urls.add(norm_url)
        if company_clean:
            seen_company_titles.add(comp_title_key)
        j.idx = len(deduped)
        deduped.append(j)

    counts["deduped"] = len(deduped)
    return deduped, counts

async def _run_source_safely(
    src_name: str,
    coro_func,
    timeout_s: float = SOURCE_TIMEOUT_SECONDS
) -> Tuple[List[Job], str, str, float]:
    """
    Executes a single source coroutine with an INDEPENDENT timeout.
    A slow or failing source never cancels or starves any other source.
    """
    start_time = time.perf_counter()
    try:
        jobs, status, reason = await asyncio.wait_for(coro_func(), timeout=timeout_s)
        elapsed = round(time.perf_counter() - start_time, 2)
        return jobs, status, reason, elapsed
    except asyncio.TimeoutError:
        elapsed = round(time.perf_counter() - start_time, 2)
        logger.warning(f"Source [{src_name}] timed out after {elapsed}s")
        return [], "timeout", f"timeout (request timed out after {elapsed}s)", elapsed
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 2)
        logger.error(f"Source [{src_name}] failed: {e}")
        return [], "error", f"error: {str(e)}", elapsed

async def search_query(
    query: SearchQuery,
    preferences: Preferences | None = None,
    max_age_days: int = 30,
) -> Tuple[List[Job], Dict[str, Dict[str, Any]]]:
    """
    Queries real live job sources concurrently for a single query.
    Each source has an INDEPENDENT timeout (default 25s).
    Returns: (deduped_jobs, source_status_map)
    """
    prefs = preferences or Preferences(max_age_days=max_age_days)
    query_str = query.q

    # Run all 5 sources concurrently with independent timeouts
    tasks = [
        _run_source_safely("Adzuna", lambda: search_adzuna(query, prefs, max_results_total=35)),
        _run_source_safely("JSearch", lambda: search_jsearch(query, preferences=prefs, max_results=15)),
        _run_source_safely("Remotive", lambda: search_remotive(query_str, max_results=12)),
        _run_source_safely("Arbeitnow", lambda: search_arbeitnow(query_str, max_results=12)),
        _run_source_safely("Greenhouse", lambda: search_greenhouse(query_str, max_results=15)),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=False)

    all_jobs: List[Job] = []
    source_names = ["Adzuna", "JSearch", "Remotive", "Arbeitnow", "Greenhouse"]
    statuses: Dict[str, Dict[str, Any]] = {}

    for idx, (jobs, status, reason, elapsed) in enumerate(results):
        src_name = source_names[idx]
        statuses[src_name] = {
            "count": len(jobs),
            "status": status,
            "reason": reason,
            "elapsed_s": elapsed,
        }
        all_jobs.extend(jobs)
        logger.info(f"Source [{src_name}] -> {status}: {reason} in {elapsed}s")

    deduped_jobs, counts = deduplicate_jobs(all_jobs)
    statuses["deduped"] = {
        "count": len(deduped_jobs),
        "status": "ok",
        "reason": f"{len(deduped_jobs)} unique real jobs after deduplication",
        "elapsed_s": round(max([s["elapsed_s"] for s in statuses.values() if "elapsed_s" in s] or [0.0]), 2),
    }

    global latest_source_counts, latest_source_statuses
    latest_source_counts = counts
    latest_source_statuses = statuses

    return deduped_jobs, statuses

async def search_all_queries(
    queries: List[SearchQuery],
    preferences: Preferences,
) -> Tuple[List[Job], Dict[str, Dict[str, Any]]]:
    """
    Executes multiple approved queries across all real sources concurrently,
    then aggregates, merges, and dedupes them while capturing structured source statuses.
    """
    if not queries:
        empty_statuses = {
            s: {"count": 0, "status": "ok", "reason": "No queries executed", "elapsed_s": 0.0}
            for s in ["Adzuna", "JSearch", "Remotive", "Arbeitnow", "Greenhouse", "deduped"]
        }
        return [], empty_statuses

    tasks = [search_query(q, preferences=preferences) for q in queries]
    query_results = await asyncio.gather(*tasks, return_exceptions=True)

    combined_jobs: List[Job] = []
    merged_statuses: Dict[str, Dict[str, Any]] = {
        "Adzuna": {"count": 0, "status": "ok", "reason": "", "elapsed_s": 0.0},
        "JSearch": {"count": 0, "status": "ok", "reason": "", "elapsed_s": 0.0},
        "Remotive": {"count": 0, "status": "ok", "reason": "", "elapsed_s": 0.0},
        "Arbeitnow": {"count": 0, "status": "ok", "reason": "", "elapsed_s": 0.0},
        "Greenhouse": {"count": 0, "status": "ok", "reason": "", "elapsed_s": 0.0},
        "deduped": {"count": 0, "status": "ok", "reason": "", "elapsed_s": 0.0},
    }

    for res in query_results:
        if isinstance(res, tuple) and len(res) == 2:
            jobs, statuses = res
            combined_jobs.extend(jobs)
            for src, info in statuses.items():
                if src in merged_statuses:
                    merged_statuses[src]["count"] += info.get("count", 0)
                    merged_statuses[src]["elapsed_s"] = max(merged_statuses[src]["elapsed_s"], info.get("elapsed_s", 0.0))
                    # If any query succeeded with jobs, status is ok
                    if info.get("count", 0) > 0:
                        merged_statuses[src]["status"] = "ok"
                    elif merged_statuses[src]["count"] == 0:
                        merged_statuses[src]["status"] = info.get("status", "ok")
                        merged_statuses[src]["reason"] = info.get("reason", "")

    deduped, counts = deduplicate_jobs(combined_jobs)

    # Finalize status reason strings
    for src in ["Adzuna", "JSearch", "Remotive", "Arbeitnow", "Greenhouse"]:
        elapsed_str = f"{merged_statuses[src]['elapsed_s']}s"
        if merged_statuses[src]["status"] == "ok":
            cnt = merged_statuses[src]["count"]
            if cnt > 0:
                merged_statuses[src]["reason"] = f"ok ({cnt} jobs)"
            else:
                merged_statuses[src]["reason"] = "ok (0 jobs for these queries)"
        elif merged_statuses[src]["status"] == "timeout":
            merged_statuses[src]["reason"] = f"timeout (after {elapsed_str})"

    merged_statuses["deduped"] = {
        "count": len(deduped),
        "status": "ok",
        "reason": f"{len(deduped)} unique real jobs",
        "elapsed_s": round(max([s["elapsed_s"] for s in merged_statuses.values() if "elapsed_s" in s] or [0.0]), 2),
    }

    global latest_source_counts, latest_source_statuses
    latest_source_counts = counts
    latest_source_statuses = merged_statuses

    return deduped, merged_statuses

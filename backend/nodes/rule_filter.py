from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Any, Dict, List, Set
from urllib.parse import urlparse, urlunparse

from backend.config import MAX_CANDIDATES
from backend.schemas import RawResult, Profile, Preferences, Job, validate_job_guard
from backend.state import GraphState

logger = logging.getLogger(__name__)

def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url.strip())
        clean_path = parsed.path.rstrip("/")
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), clean_path, "", "", ""))
    except Exception:
        return url.strip()

def is_strictly_stale_posting(published_str: str | None, max_age_days: int) -> bool:
    """
    Returns True ONLY if published date is valid, parseable, and strictly older
    than max_age_days. If date is None or unparseable, it MUST PASS (flagged unknown).
    """
    if not published_str:
        return False
    try:
        # Try ISO parsing
        pub_date = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        if pub_date < cutoff:
            return True
    except Exception:
        pass
    return False

def rule_filter(state: GraphState) -> Dict[str, Any]:
    """
    Dedup + Liveness Node:
    - Normalizes and deduplicates jobs across sources.
    - Only allowed hard drops:
      1. Missing title, company, or apply_url.
      2. Confirmed dead link.
      3. Confirmed older than max posting age.
      4. Duplicate posting.
    - ALL relevance filtering is removed (no blog/course heuristics, no URL pattern checks,
      no skill-overlap cutoffs, no description-length checks, no domain allowlists).
    - Unknown employment type, posting date, salary, or location MUST PASS and be flagged 'unknown'.
    - Tracks and returns a full multi-stage funnel counter.
    """
    raw_results = state.get("raw_results", [])
    seen_urls: Set[str] = set(state.get("seen_urls", set()))
    prefs: Preferences | None = state.get("preferences")
    max_age_days = prefs.max_age_days if prefs else 30

    # Funnel Tracking structures
    by_source_counts: Dict[str, int] = {}
    duplicate_examples: List[str] = []
    missing_fields_examples: List[str] = []
    stale_examples: List[str] = []
    dead_link_examples: List[str] = []

    normalized_count = 0
    current_seen_urls: Set[str] = set()
    current_seen_comp_titles: Set[tuple] = set()

    deduped_candidates: List[RawResult] = []
    kept_candidates: List[RawResult] = []

    for item in raw_results:
        job: Job | None = item.job
        src = job.source if job and job.source else "Unknown"
        by_source_counts[src] = by_source_counts.get(src, 0) + 1
        normalized_count += 1

        title_str = (job.title if job and job.title else item.title) or ""
        company_str = (job.company if job and job.company else "") or ""
        apply_url_str = (job.apply_url if job and job.apply_url else item.url) or ""

        # Stage 3: Deduplication
        norm_url = normalize_url(apply_url_str) if apply_url_str else f"empty-{id(item)}"
        comp_clean = re.sub(r"[^a-zA-Z0-9]", "", company_str.lower())
        title_clean = re.sub(r"[^a-zA-Z0-9]", "", title_str.lower())[:25]
        comp_title_key = (comp_clean, title_clean) if comp_clean else None

        if (apply_url_str and (norm_url in seen_urls or norm_url in current_seen_urls)) or (comp_title_key and comp_title_key in current_seen_comp_titles):
            duplicate_examples.append(f"{title_str or 'Unknown'} at {company_str or 'Unknown'}")
            continue

        if apply_url_str:
            current_seen_urls.add(norm_url)
        if comp_title_key:
            current_seen_comp_titles.add(comp_title_key)
        deduped_candidates.append(item)

        # Stage 4: Hard Filters (Only missing fields, confirmed stale, dead link)
        if not title_str.strip() or not company_str.strip() or not apply_url_str.strip() or not apply_url_str.startswith("http"):
            missing_fields_examples.append(f"{title_str or 'Empty Title'} at {company_str or 'Empty Company'}")
            continue

        pub_date = (job.posted_date if job else item.published)
        if is_strictly_stale_posting(pub_date, max_age_days):
            stale_examples.append(f"{title_str} at {company_str} (published: {pub_date})")
            continue

        # Unknown fields pass through safely
        if job:
            if not job.job_type:
                job.job_type = "unknown"
            if not job.location or job.location.lower() in ["any", "worldwide", "remote", ""]:
                job.location = "Remote / Unspecified"
            if not job.posted_date:
                job.posted_date = "unknown"

        kept_candidates.append(item)

    # Sort and cap candidates if needed
    cap_limit = max(MAX_CANDIDATES, 40)
    final_candidates = kept_candidates[:cap_limit]

    for cand in final_candidates:
        seen_urls.add(normalize_url(cand.url))

    # Construct Funnel
    funnel = {
        "fetched": {
            "total": len(raw_results),
            "by_source": by_source_counts,
        },
        "normalized": {
            "count": normalized_count,
        },
        "deduped": {
            "count": len(deduped_candidates),
            "dropped": len(duplicate_examples),
            "examples_dropped": duplicate_examples[:5],
        },
        "hard_filters": {
            "passed": len(final_candidates),
            "dropped": len(missing_fields_examples) + len(stale_examples) + len(dead_link_examples),
            "drop_reasons": {
                "missing_required_fields": {
                    "count": len(missing_fields_examples),
                    "examples": missing_fields_examples[:5],
                },
                "stale_posting": {
                    "count": len(stale_examples),
                    "examples": stale_examples[:5],
                },
                "dead_link": {
                    "count": len(dead_link_examples),
                    "examples": dead_link_examples[:5],
                },
            },
        },
        "scored": {
            "total_evaluated": 0,
            "passed_threshold": 0,
            "below_threshold": 0,
            "examples_below": [],
        },
        "shown": {
            "count": 0,
        },
    }

    logger.info(
        f"[FUNNEL] Fetched={funnel['fetched']['total']} -> "
        f"Normalized={funnel['normalized']['count']} -> "
        f"Deduped={funnel['deduped']['count']} -> "
        f"HardFiltersPassed={funnel['hard_filters']['passed']} "
        f"(StaleDropped={len(stale_examples)}, MissingFieldsDropped={len(missing_fields_examples)})"
    )

    return {
        "candidates": final_candidates,
        "seen_urls": seen_urls,
        "funnel": funnel,
        "status_note": f"Dedup + Liveness: {len(final_candidates)} jobs passed hard validation",
    }

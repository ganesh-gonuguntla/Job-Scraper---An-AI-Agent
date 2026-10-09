import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Set
from urllib.parse import urlparse, urlunparse

from backend.config import MAX_CANDIDATES
from backend.schemas import RawResult, Profile, Preferences
from backend.state import GraphState

NON_JOB_URL_PATTERNS = [
    r"/blog(?:/|$)",
    r"/articles?(?:/|$)",
    r"/category(?:/|$)",
    r"/tag(?:/|$)",
    r"/courses?(?:/|$)",
    r"/bootcamp(?:/|$)",
    r"/learn(?:/|$)",
    r"/pricing(?:/|$)",
    r"/login(?:/|$)",
    r"/signin(?:/|$)",
    r"/search(?:/|\?|$)",
    r"/browse(?:/|$)",
    r"/directory(?:/|$)",
    r"/archive(?:/|$)",
    r"how-to-",
    r"top-\d+",
    r"interview-questions",
]

NON_JOB_TEXT_KEYWORDS = [
    "enroll now",
    "course fees",
    "syllabus",
    "bootcamp curriculum",
    "interview tips",
    "frequently asked questions",
    "browse all jobs",
    "50,000+ jobs",
]

def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    # Remove fragments and tracking query params
    clean_path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), clean_path, "", "", ""))

def is_non_job_posting(url: str, title: str, text: str) -> bool:
    url_lower = url.lower()
    for pattern in NON_JOB_URL_PATTERNS:
        if re.search(pattern, url_lower):
            return True

    text_lower = (title + " " + text).lower()
    for kw in NON_JOB_TEXT_KEYWORDS:
        if kw in text_lower:
            return True

    # Too short to be a job posting
    if len(text.strip()) < 25:
        return True

    return False

def is_stale_posting(published_str: str | None, max_age_days: int) -> bool:
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

def matches_job_type_preferences(text: str, allowed_types: List[str]) -> bool:
    text_lower = text.lower()
    intern_keywords = ["intern", "internship", "stipend", "trainee"]
    fte_keywords = ["full-time", "full time", "fte", "permanent", "ctc", "lpa", "annual"]

    has_intern = any(k in text_lower for k in intern_keywords)
    has_fte = any(k in text_lower for k in fte_keywords)

    intern_allowed = "intern" in allowed_types
    fte_allowed = any(t in allowed_types for t in ["fte", "contract", "part_time"])

    if has_intern and not intern_allowed and not has_fte:
        return False
    if has_fte and not fte_allowed and not has_intern:
        return False

    return True

def compute_skill_overlap(top_skills: List[str], text: str) -> float:
    if not top_skills:
        return 0.5
    text_lower = text.lower()
    matched = 0
    for skill in top_skills:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            matched += 1
    return matched / len(top_skills)

def rule_filter(state: GraphState) -> Dict[str, Any]:
    raw_results = state.get("raw_results", [])
    seen_urls: Set[str] = set(state.get("seen_urls", set()))
    profile: Profile | None = state.get("profile")
    prefs: Preferences | None = state.get("preferences")

    max_age_days = prefs.max_age_days if prefs else 30
    allowed_types = prefs.job_types if prefs else ["fte", "intern"]
    top_skills = profile.top_skills if profile else []

    deduped_candidates: List[RawResult] = []
    current_seen_in_batch: Set[str] = set()

    for item in raw_results:
        norm_url = normalize_url(item.url)
        if norm_url in seen_urls or norm_url in current_seen_in_batch:
            continue
        current_seen_in_batch.add(norm_url)

        # 1. Non-posting check
        if is_non_job_posting(item.url, item.title, item.text):
            continue

        # 2. Stale check
        if is_stale_posting(item.published, max_age_days):
            continue

        # 3. Job type check
        if not matches_job_type_preferences(item.title + " " + item.text, allowed_types):
            continue

        # 4. Skill overlap calculation
        score = compute_skill_overlap(top_skills, item.title + " " + item.text)
        if score < 0.1:
            continue

        item.rule_score = round(score, 3)
        deduped_candidates.append(item)

    # Sort descending by rule_score
    deduped_candidates.sort(key=lambda x: x.rule_score, reverse=True)
    kept_candidates = deduped_candidates[:MAX_CANDIDATES]

    # Add kept URLs to seen_urls
    for cand in kept_candidates:
        seen_urls.add(normalize_url(cand.url))

    return {
        "candidates": kept_candidates,
        "seen_urls": seen_urls,
        "status_note": f"Filtered to {len(kept_candidates)} relevant job candidates",
    }

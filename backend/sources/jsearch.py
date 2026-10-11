import asyncio
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

import httpx

from backend.config import (
    OPENWEBNINJA_API_KEY,
    JSEARCH_BASE_URL,
    MAX_JSEARCH_CALLS_PER_RUN,
)
from backend.schemas import Job, Preferences
from backend.sources.client import get_http_client

logger = logging.getLogger(__name__)

COMMON_TECH_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "go", "rust", "php", "ruby",
    "react", "react.js", "angular", "vue", "next.js", "node.js", "nodejs", "express", "django", "fastapi",
    "flask", "spring", "spring boot", "asp.net", ".net", "sql", "postgresql", "postgres", "mysql", "mongodb",
    "redis", "elasticsearch", "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "git", "ci/cd",
    "graphql", "rest api", "microservices", "kafka", "rabbitmq", "tailwind", "html", "css", "linux"
]

COUNTRY_MAP = {
    "india": "in", "bangalore": "in", "bengaluru": "in", "hyderabad": "in", "pune": "in", "delhi": "in",
    "mumbai": "in", "chennai": "in", "noida": "in", "gurgaon": "in", "kochi": "in",
    "united states": "us", "usa": "us", "us": "us", "new york": "us", "san francisco": "us",
    "austin": "us", "seattle": "us", "chicago": "us", "california": "us",
    "united kingdom": "gb", "uk": "gb", "london": "gb", "england": "gb", "manchester": "gb",
    "canada": "ca", "toronto": "ca", "vancouver": "ca", "montreal": "ca",
    "germany": "de", "deutschland": "de", "berlin": "de", "munich": "de", "frankfurt": "de",
    "australia": "au", "sydney": "au", "melbourne": "au",
    "singapore": "sg", "france": "fr", "netherlands": "nl",
}

# In-memory response cache: cache_key -> (timestamp, List[Job])
_jsearch_cache: Dict[str, Tuple[datetime, List[Job]]] = {}
_jsearch_calls_this_run = 0
_jsearch_quota_exhausted = False

def reset_jsearch_run_counter():
    """Resets call counter for a new run."""
    global _jsearch_calls_this_run
    _jsearch_calls_this_run = 0

def extract_skills_from_text(text: str) -> List[str]:
    txt_lower = f" {text.lower()} "
    found = []
    for kw in COMMON_TECH_KEYWORDS:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, txt_lower):
            found.append(kw)
            if len(found) >= 10:
                break
    return found

def resolve_country_code(locations: List[str]) -> str:
    """
    Resolves country code for JSearch country parameter. Default 'in' if India or 'us'.
    """
    for loc in locations:
        loc_clean = loc.lower().strip()
        for token, code in COUNTRY_MAP.items():
            if token in loc_clean:
                return code
    return "in"

def map_date_posted(max_age_days: Optional[int]) -> str:
    """Maps user max_age_days to JSearch date_posted filter parameter."""
    if not max_age_days or max_age_days > 30:
        return "all"
    if max_age_days <= 1:
        return "today"
    if max_age_days <= 3:
        return "3days"
    if max_age_days <= 7:
        return "week"
    return "month"

def map_employment_types(job_types: Optional[List[str]]) -> Optional[str]:
    """
    Maps UI job_types to OpenWeb Ninja employment_types:
    fte -> FULLTIME, intern -> INTERN, contract -> CONTRACTOR, part_time -> PARTTIME
    Only returns a filter string if a strict subset is selected.
    """
    if not job_types:
        return None
    type_set = set(t.lower() for t in job_types)
    all_types = {"fte", "intern", "contract", "part_time"}
    if type_set >= all_types or len(type_set) == 0:
        return None  # All selected, no need to restrict

    mapped = []
    if "fte" in type_set:
        mapped.append("FULLTIME")
    if "intern" in type_set:
        mapped.append("INTERN")
    if "contract" in type_set:
        mapped.append("CONTRACTOR")
    if "part_time" in type_set:
        mapped.append("PARTTIME")

    return ",".join(mapped) if mapped else None

def build_openwebninja_query(query_text: str, preferences: Optional[Preferences] = None) -> Tuple[str, bool]:
    """
    Builds the natural query and detects if remote is requested.
    Returns: (clean_query, is_remote)
    """
    clean_q = re.sub(r"[^a-zA-Z0-9\s\+\#\.]", " ", query_text).strip()
    words = clean_q.split()

    is_remote = False
    location_suffix = ""

    if preferences:
        for loc in (preferences.locations or []):
            loc_l = loc.lower().strip()
            if loc_l in ["remote", "work from home", "anywhere", "worldwide", "any", "global"]:
                is_remote = True
            elif loc_l not in ["india", "usa", "us"]:
                location_suffix = f" in {loc_l}"
                break

    base = " ".join(words)
    if location_suffix and location_suffix not in base.lower():
        base = f"{base}{location_suffix}"

    return base.strip(), is_remote

async def search_jsearch(
    query_text: str,
    preferences: Optional[Preferences] = None,
    max_results: int = 15,
) -> Tuple[List[Job], str, str]:
    """
    Direct OpenWeb Ninja JSearch API adapter:
    GET https://api.openwebninja.com/jsearch/search-v2
    Auth: Header X-API-Key: OPENWEBNINJA_API_KEY
    Returns: (jobs, status, detail_message)
    Status values: 'ok', 'invalid key', 'rate limited/quota', 'not configured', 'timeout', 'error'
    """
    global _jsearch_calls_this_run, _jsearch_quota_exhausted

    if not OPENWEBNINJA_API_KEY or not OPENWEBNINJA_API_KEY.strip():
        msg = "Missing OPENWEBNINJA_API_KEY in .env"
        logger.warning(f"[JSearch] {msg}")
        return [], "not configured", msg

    if _jsearch_quota_exhausted:
        msg = "rate limited/quota (Quota exhausted on OpenWeb Ninja plan)"
        logger.info(f"[JSearch] Skipping call: {msg}")
        return [], "rate limited/quota", msg

    if _jsearch_calls_this_run >= MAX_JSEARCH_CALLS_PER_RUN:
        logger.info(f"[JSearch] Reached max calls limit ({MAX_JSEARCH_CALLS_PER_RUN}) for this run.")
        return [], "ok", "ok (call budget reached)"

    prefs = preferences or Preferences()
    if hasattr(query_text, "render_jsearch_query"):
        clean_q, query_country, is_remote = query_text.render_jsearch_query()
        country_code = query_country or resolve_country_code(prefs.locations or ["India"])
    else:
        clean_q, is_remote = build_openwebninja_query(str(query_text), prefs)
        country_code = resolve_country_code(prefs.locations or ["India"])

    date_posted_val = map_date_posted(prefs.max_age_days)
    emp_types = map_employment_types(prefs.job_types)

    # Cache Check (24h TTL)
    cache_key = f"{clean_q.lower()}:{country_code}:{is_remote}:{date_posted_val}:{emp_types}"
    if cache_key in _jsearch_cache:
        cached_time, cached_jobs = _jsearch_cache[cache_key]
        if datetime.now(timezone.utc) - cached_time < timedelta(hours=24):
            logger.info(f"[JSearch Cache Hit] Returning {len(cached_jobs)} cached jobs for '{clean_q}'")
            return cached_jobs[:max_results], "ok", f"ok ({len(cached_jobs)} jobs)"

    base_url = (JSEARCH_BASE_URL or "https://api.openwebninja.com/jsearch").rstrip("/")
    endpoint = f"{base_url}/search-v2"
    headers = {
        "X-API-Key": OPENWEBNINJA_API_KEY.strip(),
    }
    params: Dict[str, Any] = {
        "query": clean_q,
        "country": country_code,
        "num_pages": 1,
    }

    if is_remote:
        params["work_from_home"] = "true"
    if date_posted_val != "all":
        params["date_posted"] = date_posted_val
    if emp_types:
        params["employment_types"] = emp_types

    # Redacted log URL
    redacted_url = f"{endpoint}?query={clean_q}&country={country_code}&num_pages=1 [X-API-Key: REDACTED]"

    try:
        _jsearch_calls_this_run += 1
        logger.info(f"[JSearch Call #{_jsearch_calls_this_run}] URL: {redacted_url}")

        client = get_http_client()
        resp = await client.get(endpoint, headers=headers, params=params, timeout=22.0)

        status_code = resp.status_code
        trunc_body = resp.text[:200].replace("\n", " ")
        logger.info(f"[JSearch HTTP {status_code}] Response: {trunc_body}")

        if status_code == 200:
            payload = resp.json()
            data_container = payload.get("data", {})
            # In /search-v2, jobs list is under data.jobs
            raw_jobs = data_container.get("jobs", []) if isinstance(data_container, dict) else (data_container if isinstance(data_container, list) else [])

            jobs: List[Job] = []
            now_iso = datetime.now(timezone.utc).isoformat()

            for item in raw_jobs[:max_results]:
                title = item.get("job_title")
                company = item.get("employer_name")

                # Apply link resolution
                apply_link = item.get("job_apply_link")
                if not apply_link and item.get("apply_options"):
                    apply_link = item.get("apply_options")[0].get("apply_link")
                if not apply_link:
                    apply_link = item.get("job_google_link")

                # Drop condition: Must have title, employer, and apply link
                if not title or not company or not apply_link:
                    continue

                location_val = item.get("job_location")
                if not location_val:
                    city = item.get("job_city") or ""
                    state = item.get("job_state") or ""
                    c_code = item.get("job_country") or ""
                    location_val = f"{city}, {state}".strip(", ") or c_code or "Not Specified"

                desc = item.get("job_description", "")
                skills = extract_skills_from_text(f"{title} {desc}")

                job_id = str(item.get("job_id", "") or item.get("job_uid", ""))

                job = Job(
                    source="JSearch",
                    source_job_id=job_id,
                    title=title.strip(),
                    company=company.strip(),
                    location=location_val,
                    remote=bool(item.get("job_is_remote")),
                    apply_url=apply_link,
                    url=apply_link,
                    description=desc[:2500],
                    description_is_partial=False,
                    salary_min=item.get("job_min_salary"),
                    salary_max=item.get("job_max_salary"),
                    salary_period="year" if str(item.get("job_salary_period") or "").lower() == "year" else ("month" if str(item.get("job_salary_period") or "").lower() == "month" else "unknown"),
                    posted_date=item.get("job_posted_at_datetime_utc") or item.get("job_posted_at"),
                    fetched_at=now_iso,
                    skills_required=skills,
                    raw_payload={
                        "job_id": job_id,
                        "publisher": item.get("job_publisher"),
                        "employer_website": item.get("employer_website"),
                    }
                )
                jobs.append(job)

            # Store in cache
            _jsearch_cache[cache_key] = (datetime.now(timezone.utc), jobs)

            if jobs:
                return jobs, "ok", f"ok ({len(jobs)} jobs)"
            return [], "ok", "ok (0 jobs for these queries)"

        elif status_code in (401, 403):
            reason = f"invalid key (HTTP {status_code}: Bad OpenWeb Ninja API key)"
            logger.error(f"[JSearch Auth] {reason}")
            return [], "invalid key", reason

        elif status_code == 429:
            _jsearch_quota_exhausted = True
            reason = "rate limited/quota (HTTP 429: OpenWeb Ninja credits or rate limit exhausted)"
            logger.warning(f"[JSearch Quota] {reason}")
            return [], "rate limited/quota", reason

        elif status_code == 404:
            reason = f"endpoint not found (HTTP 404: {trunc_body})"
            logger.error(f"[JSearch 404] {reason}")
            return [], "endpoint not found (HTTP 404)", reason

        elif status_code >= 500:
            reason = f"server error (HTTP {status_code})"
            logger.error(f"[JSearch 5xx] {reason}")
            return [], f"server error (HTTP {status_code})", reason

        else:
            reason = f"error (HTTP {status_code}: {trunc_body})"
            logger.error(f"[JSearch Error] {reason}")
            return [], "error", reason

    except httpx.TimeoutException:
        reason = "timeout (OpenWeb Ninja request timed out after 12s)"
        logger.error(f"[JSearch Timeout] {reason}")
        return [], "timeout", reason
    except Exception as e:
        reason = f"error ({str(e)})"
        logger.error(f"[JSearch Exception] {reason}")
        return [], "error", reason

import asyncio
from datetime import datetime, timezone
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

import httpx

from backend.config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    ADZUNA_DEFAULT_COUNTRIES,
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

STOP_WORDS = {
    "job", "jobs", "hiring", "openings", "opening", "vacancy", "vacancies", "wanted",
    "role", "roles", "position", "positions", "looking", "for", "in", "at", "and", "or", "with"
}

COUNTRY_MAP = {
    "india": "in", "bangalore": "in", "bengaluru": "in", "hyderabad": "in", "pune": "in", "delhi": "in", "mumbai": "in", "chennai": "in", "noida": "in", "gurgaon": "in",
    "united states": "us", "usa": "us", "us": "us", "new york": "us", "san francisco": "us", "austin": "us", "seattle": "us", "chicago": "us", "california": "us",
    "united kingdom": "gb", "uk": "gb", "london": "gb", "england": "gb", "manchester": "gb",
    "canada": "ca", "toronto": "ca", "vancouver": "ca", "montreal": "ca",
    "australia": "au", "sydney": "au", "melbourne": "au",
    "germany": "de", "deutschland": "de", "berlin": "de", "munich": "de", "frankfurt": "de",
    "france": "fr", "paris": "fr",
    "netherlands": "nl", "amsterdam": "nl",
    "singapore": "sg",
    "poland": "pl",
    "brazil": "br",
    "italy": "it",
    "spain": "es",
    "switzerland": "ch",
    "south africa": "za",
    "new zealand": "nz",
}

# Semaphore to avoid bursting the Adzuna trial rate limit
_adzuna_sem = asyncio.Semaphore(1)
_adzuna_calls_made = 0

def resolve_country_code(locations: List[str]) -> Optional[str]:
    """
    Determines Adzuna ISO country code from user target locations.
    Returns None if Any / Worldwide / Remote is requested.
    """
    for loc in locations:
        loc_clean = loc.lower().strip()
        if loc_clean in ["any", "worldwide", "global", "remote"]:
            continue
        for token, code in COUNTRY_MAP.items():
            if token in loc_clean:
                return code
    return None

def extract_focused_keywords(query_text: str) -> str:
    """
    Extracts a few focused keywords for Adzuna what_or query.
    Removes noise words (jobs, hiring, punctuation) and selects core tech/title terms (max 4).
    """
    clean = re.sub(r"[^a-zA-Z0-9\s\+\#\.]", " ", query_text).lower()
    tokens = [t.strip() for t in clean.split() if t.strip()]
    focused = [t for t in tokens if t not in STOP_WORDS]
    if not focused:
        focused = tokens
    return " ".join(focused[:4])

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

def redact_credentials(url: str) -> str:
    redacted = url
    if ADZUNA_APP_KEY:
        redacted = redacted.replace(ADZUNA_APP_KEY, "[REDACTED_APP_KEY]")
    if ADZUNA_APP_ID:
        redacted = redacted.replace(ADZUNA_APP_ID, "[REDACTED_APP_ID]")
    return redacted

async def query_adzuna_api(
    country: str,
    what_or_keywords: str,
    where_location: Optional[str] = None,
    max_days_old: Optional[int] = None,
    job_types: Optional[List[str]] = None,
    page: int = 1,
    results_per_page: int = 20,
) -> Tuple[List[Job], str, str]:
    """
    Calls Adzuna endpoint https://api.adzuna.com/v1/api/jobs/{country}/search/{page}.
    Returns: (jobs, status, detail_message)
    Status values: 'ok', 'auth failed', 'rate limited', 'not configured', 'timeout', 'error'
    """
    global _adzuna_calls_made

    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        msg = "Missing ADZUNA_APP_ID or ADZUNA_APP_KEY in .env"
        logger.warning(f"[Adzuna] {msg}")
        return [], "not configured", msg

    endpoint = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
    params: Dict[str, Any] = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": results_per_page,
        "what_or": what_or_keywords,
        "content-type": "application/json",
    }

    if where_location and where_location.lower() not in ["any", "worldwide", "global", "remote"]:
        params["where"] = where_location

    if max_days_old and max_days_old > 0:
        params["max_days_old"] = max_days_old

    if job_types:
        if "fte" in job_types:
            params["full_time"] = 1
        if "part_time" in job_types:
            params["part_time"] = 1
        if "contract" in job_types:
            params["contract"] = 1

    req_url = f"{endpoint}?" + "&".join(f"{k}={v}" for k, v in params.items())
    redacted_url = redact_credentials(req_url)

    try:
        async with _adzuna_sem:
            await asyncio.sleep(0.3)
            _adzuna_calls_made += 1

            client = get_http_client()
            resp = await client.get(endpoint, params=params, timeout=20.0)

            status_code = resp.status_code
            trunc_body = resp.text[:250].replace("\n", " ")
            logger.info(f"[Adzuna HTTP {status_code}] URL: {redacted_url} | Response: {trunc_body}")

            if status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                jobs: List[Job] = []
                now_iso = datetime.now(timezone.utc).isoformat()

                for item in results:
                    title = item.get("title")
                    company_info = item.get("company", {})
                    company_name = company_info.get("display_name") if isinstance(company_info, dict) else str(company_info)
                    redirect_url = item.get("redirect_url")
                    loc_info = item.get("location", {})
                    location_name = loc_info.get("display_name") if isinstance(loc_info, dict) else "Not Specified"
                    desc = item.get("description", "")

                    if not title or not company_name or not redirect_url:
                        continue

                    clean_title = re.sub(r"<[^>]+>", "", title).strip()
                    clean_desc = re.sub(r"<[^>]+>", "", desc).strip()
                    clean_company = re.sub(r"<[^>]+>", "", company_name).strip()
                    is_pred = bool(item.get("salary_is_predicted") == 1 or item.get("salary_is_predicted") is True)
                    skills = extract_skills_from_text(f"{clean_title} {clean_desc}")

                    is_remote = False
                    if "remote" in clean_title.lower() or "remote" in location_name.lower() or "work from home" in clean_desc.lower():
                        is_remote = True

                    job = Job(
                        source="Adzuna",
                        source_job_id=str(item.get("id", "")),
                        title=clean_title,
                        company=clean_company,
                        location=location_name or "Not Specified",
                        remote=is_remote,
                        apply_url=redirect_url,
                        url=redirect_url,
                        description=clean_desc[:2500],
                        description_is_partial=True,
                        salary_min=item.get("salary_min"),
                        salary_max=item.get("salary_max"),
                        salary_is_predicted=is_pred,
                        posted_date=item.get("created"),
                        fetched_at=now_iso,
                        skills_required=skills,
                        raw_payload={
                            "id": item.get("id"),
                            "category": item.get("category"),
                            "country": country,
                        }
                    )
                    jobs.append(job)

                if jobs:
                    return jobs, "ok", f"ok ({len(jobs)} jobs)"
                else:
                    return [], "ok", "ok (0 jobs for these queries)"

            elif status_code in (401, 403):
                reason = f"auth failed (HTTP {status_code}: Invalid Adzuna credentials)"
                logger.error(f"[Adzuna Auth Failed] {reason} | URL: {redacted_url}")
                return [], "auth failed", reason

            elif status_code == 429:
                reason = "rate limited (HTTP 429: Adzuna trial API request limit reached)"
                logger.warning(f"[Adzuna Rate Limited] {reason} | URL: {redacted_url}")
                return [], "rate limited", reason

            else:
                reason = f"error (HTTP {status_code}: {trunc_body})"
                logger.error(f"[Adzuna Error] {reason} | URL: {redacted_url}")
                return [], "error", reason

    except httpx.TimeoutException:
        reason = "timeout (Adzuna request timed out after 12s)"
        logger.error(f"[Adzuna Timeout] {reason} | URL: {redacted_url}")
        return [], "timeout", reason
    except Exception as e:
        reason = f"error ({str(e)})"
        logger.error(f"[Adzuna Exception] {reason} | URL: {redacted_url}")
        return [], "error", reason

async def search_adzuna(
    query_text: str,
    preferences: Preferences,
    max_results_total: int = 35,
) -> Tuple[List[Job], str, str]:
    """
    Orchestrates Adzuna search:
    - Uses focused keywords with what_or.
    - Resolves target country or tries fallback countries in sequence if first returns 0 jobs.
    - Omits 'where' when location is Any or Remote.
    - Returns (jobs, status_code_string, detail_message).
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return [], "not configured", "Missing ADZUNA_APP_ID or ADZUNA_APP_KEY in .env"

    if hasattr(query_text, "render_adzuna_what_or"):
        what_or = query_text.render_adzuna_what_or()
    else:
        what_or = extract_focused_keywords(str(query_text))

    if not what_or:
        what_or = "analyst developer"

    primary_country = resolve_country_code(preferences.locations)
    max_days = preferences.max_age_days if preferences.max_age_days and preferences.max_age_days > 0 else None
    job_types = preferences.job_types

    # Determine where filter
    where_val = None
    for loc in preferences.locations:
        loc_l = loc.lower().strip()
        if loc_l not in ["any", "worldwide", "global", "remote", "india", "united states", "usa", "uk", "germany", "canada"]:
            where_val = loc
            break

    # Build sequence of countries to query: primary country first, then fallbacks
    country_order = []
    if primary_country:
        country_order.append(primary_country)
    for c in ADZUNA_DEFAULT_COUNTRIES:
        if c not in country_order:
            country_order.append(c)

    all_jobs: List[Job] = []
    last_status = "ok"
    last_reason = "ok (0 jobs for these queries)"

    for c in country_order[:3]:  # Try up to top 3 countries in order
        jobs, status, reason = await query_adzuna_api(
            country=c,
            what_or_keywords=what_or,
            where_location=where_val if c == primary_country else None,
            max_days_old=max_days,
            job_types=job_types,
            page=1,
            results_per_page=max_results_total,
        )

        last_status = status
        last_reason = reason

        if status in ("auth failed", "rate limited", "not configured"):
            # Hard stop on fatal credential or quota issues
            return jobs, status, reason

        if jobs:
            all_jobs.extend(jobs)
            logger.info(f"[Adzuna Success] Found {len(jobs)} jobs in country '{c}' for what_or='{what_or}'")
            break  # Successfully found jobs!

    if all_jobs:
        return all_jobs[:max_results_total], "ok", f"ok ({len(all_jobs)} jobs)"
    return [], last_status, last_reason

def get_adzuna_usage_count() -> int:
    return _adzuna_calls_made

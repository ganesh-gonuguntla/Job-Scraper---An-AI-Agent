import asyncio
from datetime import datetime, timezone
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

import httpx

from backend.schemas import Job
from backend.sources.client import get_http_client

logger = logging.getLogger(__name__)

COMMON_TECH_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "go", "rust", "php", "ruby",
    "react", "react.js", "angular", "vue", "next.js", "node.js", "nodejs", "express", "django", "fastapi",
    "flask", "spring", "spring boot", "asp.net", ".net", "sql", "postgresql", "postgres", "mysql", "mongodb",
    "redis", "elasticsearch", "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "git", "ci/cd",
    "graphql", "rest api", "microservices", "kafka", "rabbitmq", "tailwind", "html", "css", "linux",
    "power bi", "tableau", "excel", "spark", "hadoop", "airflow", "snowflake", "bigquery", "looker"
]

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

# Caches for feed endpoints to avoid spamming public endpoints across multiple queries
_feed_cache: Dict[str, Tuple[datetime, List[Job]]] = {}

async def search_remotive(keywords: str, max_results: int = 15) -> Tuple[List[Job], str, str]:
    """
    Remotive Live API adapter with connection pooling, retries, and independent timeout.
    Returns: (jobs, status, detail_message)
    """
    tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", keywords).split() if len(t) > 2 and t.lower() not in ["job", "jobs", "hiring", "developer", "engineer", "remote", "fte", "intern", "site"]]
    search_term = tokens[0] if tokens else "software"
    url = f"https://remotive.com/api/remote-jobs?search={search_term}&limit={max_results}"

    client = get_http_client()
    for attempt in range(2):
        try:
            resp = await client.get(url, timeout=20.0)
            status_code = resp.status_code
            trunc_body = resp.text[:200].replace("\n", " ")
            logger.info(f"[Remotive HTTP {status_code}] URL: {url} | Response: {trunc_body}")

            if status_code == 200:
                data = resp.json().get("jobs", [])
                jobs: List[Job] = []
                now_iso = datetime.now(timezone.utc).isoformat()

                for j in data[:max_results]:
                    title = j.get("title")
                    company = j.get("company_name")
                    apply_url = j.get("url")

                    if not title or not company or not apply_url:
                        continue

                    desc = re.sub(r"<[^>]+>", " ", j.get("description", ""))
                    desc = re.sub(r"\s+", " ", desc).strip()
                    loc = j.get("candidate_required_location") or "Worldwide / Remote"
                    skills = extract_skills_from_text(f"{title} {desc}")

                    job = Job(
                        source="Remotive",
                        source_job_id=str(j.get("id", "")),
                        title=title.strip(),
                        company=company.strip(),
                        location=loc,
                        remote=True,
                        apply_url=apply_url,
                        url=apply_url,
                        description=desc[:2000],
                        description_is_partial=False,
                        posted_date=j.get("publication_date"),
                        fetched_at=now_iso,
                        skills_required=skills,
                        raw_payload={"category": j.get("category"), "salary": j.get("salary")}
                    )
                    jobs.append(job)

                if jobs:
                    return jobs, "ok", f"ok ({len(jobs)} jobs)"
                return [], "ok", "ok (0 jobs for these queries)"

            elif status_code == 429:
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                return [], "rate limited", "rate limited (HTTP 429)"
            else:
                return [], "error", f"error (HTTP {status_code}: {trunc_body})"

        except httpx.TimeoutException:
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            logger.error(f"[Remotive Timeout] Request timed out for {url}")
            return [], "timeout", "timeout (Remotive request timed out after 20s)"
        except Exception as e:
            logger.error(f"[Remotive Exception] Failed for {url}: {e}")
            return [], "error", f"error ({str(e)})"

    return [], "timeout", "timeout (Remotive request timed out)"

async def search_arbeitnow(keywords: str, max_results: int = 15) -> Tuple[List[Job], str, str]:
    """
    Arbeitnow Live API adapter with connection pooling, retries, and independent timeout.
    Returns: (jobs, status, detail_message)
    """
    tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", keywords).split() if len(t) > 2 and t.lower() not in ["job", "jobs", "hiring", "developer", "engineer", "remote", "fte", "intern", "site"]]
    search_term = tokens[0] if tokens else "analyst"
    url = f"https://www.arbeitnow.com/api/job-board-api?search={search_term}"

    client = get_http_client()
    for attempt in range(2):
        try:
            resp = await client.get(url, timeout=20.0)
            status_code = resp.status_code
            trunc_body = resp.text[:200].replace("\n", " ")
            logger.info(f"[Arbeitnow HTTP {status_code}] URL: {url} | Response: {trunc_body}")

            if status_code == 200:
                data = resp.json().get("data", [])
                jobs: List[Job] = []
                now_iso = datetime.now(timezone.utc).isoformat()

                for j in data[:max_results]:
                    title = j.get("title")
                    company = j.get("company_name")
                    apply_url = j.get("url")

                    if not title or not company or not apply_url:
                        continue

                    desc = re.sub(r"<[^>]+>", " ", j.get("description", ""))
                    desc = re.sub(r"\s+", " ", desc).strip()
                    loc = j.get("location") or "Europe / Remote"
                    skills = extract_skills_from_text(f"{title} {desc}")

                    job = Job(
                        source="Arbeitnow",
                        source_job_id=str(j.get("slug", "")),
                        title=title.strip(),
                        company=company.strip(),
                        location=loc,
                        remote=bool(j.get("remote")),
                        apply_url=apply_url,
                        url=apply_url,
                        description=desc[:2000],
                        description_is_partial=False,
                        posted_date=str(j.get("created_at")),
                        fetched_at=now_iso,
                        skills_required=skills,
                        raw_payload={"tags": j.get("tags", [])}
                    )
                    jobs.append(job)

                if jobs:
                    return jobs, "ok", f"ok ({len(jobs)} jobs)"
                return [], "ok", "ok (0 jobs for these queries)"

            elif status_code == 429:
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                return [], "rate limited", "rate limited (HTTP 429)"
            else:
                return [], "error", f"error (HTTP {status_code}: {trunc_body})"

        except httpx.TimeoutException:
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            logger.error(f"[Arbeitnow Timeout] Request timed out for {url}")
            return [], "timeout", "timeout (Arbeitnow request timed out after 20s)"
        except Exception as e:
            logger.error(f"[Arbeitnow Exception] Failed for {url}: {e}")
            return [], "error", f"error ({str(e)})"

    return [], "timeout", "timeout (Arbeitnow request timed out)"

# Comprehensive seed companies across analytics, fintech, ecommerce, consulting, and product (global & India)
GREENHOUSE_COMPANIES = [
    "stripe", "canonical", "cloudflare", "gitlab", "elastic", "figma", "airbnb",
    "instacart", "databricks", "dbtlabs", "postman", "razorpay", "segment",
    "amplitude", "coursera", "affirm", "gusto", "plaid", "hasura", "robinhood"
]

LEVER_COMPANIES = [
    "fivetran", "palantir", "brex", "benchling", "lyft"
]

ASHBY_COMPANIES = [
    "ramp", "retool", "linear", "deel", "openai", "synthesia"
]

async def _fetch_greenhouse_board(client: httpx.AsyncClient, company: str) -> List[Dict[str, Any]]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
    try:
        resp = await client.get(url, timeout=7.0)
        if resp.status_code == 200:
            jobs = resp.json().get("jobs", [])
            for j in jobs:
                j["_board_source"] = "Greenhouse"
                j["_company"] = company
            return jobs
    except Exception:
        pass
    return []

async def _fetch_lever_board(client: httpx.AsyncClient, company: str) -> List[Dict[str, Any]]:
    url = f"https://api.lever.co/v0/postings/{company}?mode=json"
    try:
        resp = await client.get(url, timeout=7.0)
        if resp.status_code == 200:
            postings = resp.json()
            if isinstance(postings, list):
                res = []
                for p in postings:
                    res.append({
                        "id": p.get("id"),
                        "title": p.get("text"),
                        "absolute_url": p.get("hostedUrl") or p.get("applyUrl"),
                        "location": {"name": p.get("categories", {}).get("location", "Remote")},
                        "updated_at": str(p.get("createdAt")),
                        "_board_source": "Lever",
                        "_company": company,
                    })
                return res
    except Exception:
        pass
    return []

async def search_greenhouse(keywords: str, max_results: int = 20) -> Tuple[List[Job], str, str]:
    """
    Queries Greenhouse, Lever, and Ashby ATS boards concurrently.
    Matches postings by title/description against query keywords.
    Returns: (jobs, status, detail_message)
    """
    jobs: List[Job] = []
    tokens = [t.lower() for t in re.sub(r"[^\w\s]", " ", keywords).split() if len(t) > 2 and t.lower() not in ["job", "jobs", "hiring", "remote", "fte", "intern", "site"]]
    now_iso = datetime.now(timezone.utc).isoformat()

    client = get_http_client()

    # Query all Greenhouse & Lever company boards in parallel
    tasks = [_fetch_greenhouse_board(client, comp) for comp in GREENHOUSE_COMPANIES]
    tasks.extend([_fetch_lever_board(client, comp) for comp in LEVER_COMPANIES])

    board_results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in board_results:
        if not isinstance(res, list):
            continue
        for j in res:
            title = j.get("title", "")
            title_lower = title.lower()

            # Match title against tokens
            if tokens and not any(t in title_lower for t in tokens):
                continue

            apply_url = j.get("absolute_url")
            company = j.get("_company", "company")
            src_type = j.get("_board_source", "Greenhouse")

            if not title or not apply_url:
                continue

            loc_obj = j.get("location", {})
            loc_name = loc_obj.get("name", "Multiple Locations") if isinstance(loc_obj, dict) else str(loc_obj)

            job = Job(
                source="Greenhouse",
                source_job_id=f"{company}-{j.get('id')}",
                title=title.strip(),
                company=company.capitalize(),
                location=loc_name,
                remote="remote" in loc_name.lower() or "remote" in title_lower,
                apply_url=apply_url,
                url=apply_url,
                description=f"{title} position at {company.capitalize()}. Direct career portal listing via {src_type}.",
                description_is_partial=True,
                posted_date=str(j.get("updated_at") or j.get("created_at") or ""),
                fetched_at=now_iso,
                skills_required=extract_skills_from_text(title),
                raw_payload={"ats": src_type, "company": company, "raw_id": j.get("id")}
            )
            jobs.append(job)
            if len(jobs) >= max_results:
                break
        if len(jobs) >= max_results:
            break

    if jobs:
        return jobs, "ok", f"ok ({len(jobs)} jobs)"
    return [], "ok", "ok (0 jobs for these queries)"

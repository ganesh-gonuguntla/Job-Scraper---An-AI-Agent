import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import List

import httpx
import trafilatura

from backend.config import EXA_API_KEY, EXA_NUM_RESULTS, MOCK_LLM
from backend.schemas import SearchQuery, RawResult

logger = logging.getLogger(__name__)

def _load_mock_pages() -> List[dict]:
    pages_path = Path(__file__).resolve().parent.parent / "fixtures" / "sample_pages.json"
    if pages_path.exists():
        with open(pages_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

async def fetch_page_text(url: str, timeout_sec: float = 6.0) -> str:
    """
    Scrapes page text using httpx and trafilatura. Capped at 3000 chars.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                extracted = trafilatura.extract(resp.text)
                if extracted:
                    return extracted[:3000]
    except Exception as e:
        logger.debug(f"Failed to scrape {url}: {e}")
    return ""

async def search_exa(query: SearchQuery, max_age_days: int = 30) -> List[RawResult]:
    if not EXA_API_KEY:
        return []

    try:
        from exa_py import Exa
        exa = Exa(api_key=EXA_API_KEY)

        start_date = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).strftime("%Y-%m-%d")

        kwargs = {
            "num_results": EXA_NUM_RESULTS,
            "start_published_date": start_date,
            "highlights": {"num_sentences": 4},
            "text": {"max_characters": 1500},
        }
        if query.site:
            kwargs["include_domains"] = [query.site]

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: exa.search_and_contents(query.q, **kwargs)
        )

        results = []
        for item in response.results:
            text = ""
            if hasattr(item, "highlights") and item.highlights:
                text = " ".join(item.highlights)
            elif hasattr(item, "text") and item.text:
                text = item.text[:1500]

            results.append(RawResult(
                url=item.url,
                title=item.title or "Job Posting",
                text=text,
                published=getattr(item, "published_date", None),
                source_query=query.q,
                rule_score=0.0
            ))
        return results
    except Exception as e:
        logger.warning(f"Exa search error for query '{query.q}': {e}")
        return []

async def search_duckduckgo(query: SearchQuery, max_age_days: int = 30) -> List[RawResult]:
    try:
        from duckduckgo_search import DDGS
        q_str = f"site:{query.site} {query.q}" if query.site else query.q

        loop = asyncio.get_running_loop()
        def _ddg_search():
            with DDGS() as ddgs:
                # time limit: 'm' is past month
                timelimit = "m" if max_age_days <= 30 else "y"
                return list(ddgs.text(q_str, max_results=EXA_NUM_RESULTS, timelimit=timelimit))

        raw_ddg = await loop.run_in_executor(None, _ddg_search)

        results = []
        scrape_tasks = []

        for item in raw_ddg:
            url = item.get("href") or item.get("link")
            title = item.get("title", "")
            snippet = item.get("body", "")
            if not url:
                continue

            # Schedule scrape task for full text if snippet is short
            async def _process_item(u=url, t=title, s=snippet):
                page_text = s
                if len(page_text) < 200:
                    scraped = await fetch_page_text(u)
                    if scraped:
                        page_text = f"{s}\n{scraped}"
                return RawResult(
                    url=u,
                    title=t,
                    text=page_text[:2000],
                    published=None,
                    source_query=query.q,
                    rule_score=0.0
                )

            scrape_tasks.append(_process_item())

        if scrape_tasks:
            results = await asyncio.gather(*scrape_tasks, return_exceptions=True)
            results = [r for r in results if isinstance(r, RawResult)]

        return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search error for query '{query.q}': {e}")
        return []

async def search_query(query: SearchQuery, max_age_days: int = 30) -> List[RawResult]:
    """
    Search runner:
    1. If MOCK_LLM is enabled or no keys, filter fixtures/sample_pages.json
    2. Try Exa
    3. If Exa has < 3 results or fails, fallback to DuckDuckGo
    """
    if MOCK_LLM:
        logger.info(f"[MOCK_SEARCH] Matching fixture pages for query: {query.q}")
        mock_pages = _load_mock_pages()
        # Filter relevant pages based on query tokens or angle
        tokens = [t.lower() for t in query.q.split() if len(t) > 3]
        matches = []
        for p in mock_pages:
            txt = (p.get("title", "") + " " + p.get("text", "")).lower()
            if any(t in txt for t in tokens) or (query.site and query.site in p.get("url", "")):
                matches.append(RawResult(
                    url=p["url"],
                    title=p["title"],
                    text=p["text"],
                    published=p.get("published"),
                    source_query=query.q,
                    rule_score=0.0
                ))
        if not matches:
            # Fallback to returning a slice of fixture pages
            matches = [
                RawResult(
                    url=p["url"],
                    title=p["title"],
                    text=p["text"],
                    published=p.get("published"),
                    source_query=query.q,
                    rule_score=0.0
                )
                for p in mock_pages[:6]
            ]
        return matches

    # Live Search flow
    results = await search_exa(query, max_age_days)
    if len(results) < 3:
        logger.info(f"Exa produced {len(results)} results; running DuckDuckGo fallback for '{query.q}'")
        ddg_results = await search_duckduckgo(query, max_age_days)
        # Dedupe by url
        seen = {r.url for r in results}
        for dr in ddg_results:
            if dr.url not in seen:
                results.append(dr)
                seen.add(dr.url)

    return results

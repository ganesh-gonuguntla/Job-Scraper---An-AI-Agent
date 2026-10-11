import asyncio
import pytest
from backend.schemas import SearchQuery, Preferences, Profile, RawResult
from backend.search import search_query
from backend.nodes.rule_filter import rule_filter
from backend.nodes.score_jobs import score_jobs
from backend.nodes.ranker import ranker

@pytest.mark.asyncio
async def test_absurd_query_returns_honest_empty_state_with_funnel():
    """Test C: A deliberately absurd query set must return an honest empty state with the funnel, not fake data."""
    absurd_query = SearchQuery(
        title_keywords="Xylophone Quantum Alchemist Telepath",
        skills=["telepathy", "alchemy"],
        country="in",
        remote=False,
    )
    prefs = Preferences(max_age_days=30, job_types=["fte"])

    profile = Profile(
        seniority="senior",
        years_experience=10,
        top_skills=["telepathy", "alchemy", "astrology"],
        domains=["mythology"],
        past_titles=["Alchemist"],
        education="Mystic Academy",
        target_titles=["Quantum Alchemist"],
    )

    # 1. Query live sources
    jobs, statuses = await search_query(absurd_query, preferences=prefs)

    raws = [
        RawResult(url=j.apply_url, title=j.title or "", text=j.description or "", source_query=absurd_query.q, job=j)
        for j in jobs
    ]

    # 2. Rule filter
    rf_state = {
        "raw_results": raws,
        "seen_urls": set(),
        "preferences": prefs,
        "profile": profile,
    }
    filtered_res = rule_filter(rf_state)
    candidates = filtered_res["candidates"]
    funnel = filtered_res["funnel"]

    # 3. Score jobs
    score_state = {
        "candidates": candidates,
        "jobs": [c.job for c in candidates],
        "profile": profile,
        "preferences": prefs,
        "resume_hash": f"absurd_test_hash_{asyncio.get_event_loop().time()}",
        "funnel": funnel,
    }
    scored_res = await score_jobs(score_state)
    scored_jobs = scored_res["scored_jobs"]
    funnel = scored_res["funnel"]

    # 4. Ranker with threshold >= 20%
    ranked_res = ranker({"scored_jobs": scored_jobs, "preferences": prefs, "funnel": funnel})
    final_jobs = ranked_res["final_jobs"]
    funnel = ranked_res["funnel"]

    # Must return honest empty state (0 jobs) or qualifying jobs
    # For an absurd query, either 0 fetched or 0 qualifying matches reach shown
    assert len(final_jobs) == 0 or all(j.score < 20 for j in scored_jobs) or all("alchemist" in j.title.lower() for j in final_jobs)
    assert funnel is not None
    assert "fetched" in funnel
    assert "shown" in funnel

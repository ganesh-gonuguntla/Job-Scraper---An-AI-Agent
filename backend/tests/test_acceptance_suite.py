import asyncio
import time
import pytest
from backend.schemas import Job, RawResult, SearchQuery, Preferences, validate_job_guard
from backend.nodes.rule_filter import rule_filter
from backend.nodes.profile_and_queries import sanitize_and_expand_queries
from backend.schemas import Profile
from backend.search import _run_source_safely

def test_filter_never_drops_unknown_type_date_salary():
    """Test D1: The filter never drops jobs with unknown type, date, or salary."""
    job_unknown = Job(
        title="Data Analyst",
        company="TechCorp Analytics",
        apply_url="https://example.com/apply/123",
        url="https://example.com/apply/123",
        source="Adzuna",
        location=None,      # unknown
        job_type=None,      # unknown
        posted_date=None,   # unknown
        salary_min=None,    # unknown
        salary_max=None,
    )

    raw_item = RawResult(
        url=job_unknown.apply_url,
        title=f"{job_unknown.title} at {job_unknown.company}",
        text="SQL Python data analyst position",
        published=None,
        source_query="data analyst",
        job=job_unknown
    )

    state = {
        "raw_results": [raw_item],
        "seen_urls": set(),
        "preferences": Preferences(max_age_days=30),
    }

    res = rule_filter(state)
    candidates = res["candidates"]
    funnel = res["funnel"]

    # Must pass
    assert len(candidates) == 1, "Job with unknown fields was improperly dropped!"
    passed_job = candidates[0].job
    assert passed_job.job_type == "unknown"
    assert passed_job.posted_date == "unknown"
    assert funnel["hard_filters"]["passed"] == 1
    assert funnel["hard_filters"]["dropped"] == 0

def test_query_builder_never_emits_site_or_filler_words():
    """Test D2: Query builder never emits site: operators or filler words."""
    dirty_input = {
        "title_keywords": "site:linkedin.com/jobs Data Analyst hiring openings fte jobs remote",
        "skills": ["SQL", "Python"],
        "location": "Worldwide",
    }

    query = SearchQuery.model_validate(dirty_input)

    # Asserts
    assert "site:" not in query.title_keywords.lower()
    assert "linkedin.com" not in query.title_keywords.lower()
    for filler in ["jobs", "job", "hiring", "openings", "fte", "careers"]:
        assert filler not in query.title_keywords.lower().split()
    assert "remote" not in query.title_keywords.lower().split()
    assert query.remote is True  # remote was properly extracted
    assert query.location is None  # 'Worldwide' was sanitized to None
    assert query.title_keywords == "Data Analyst"

def test_query_sanitizer_and_expansion_generates_diverse_queries():
    """Test D2b: Generates 6-10 diverse queries with no filler words."""
    profile = Profile(
        seniority="entry",
        years_experience=1.5,
        top_skills=["sql", "python", "power bi", "tableau"],
        domains=["analytics"],
        past_titles=["Junior Analyst"],
        education="B.Tech",
        target_titles=["Data Analyst"],
    )

    raw_queries = [
        SearchQuery(title_keywords="Data Analyst", skills=["sql", "python"], country="in"),
        SearchQuery(title_keywords="Business Analyst", skills=["power bi"], country="in"),
    ]

    expanded = sanitize_and_expand_queries(raw_queries, profile, is_any_loc=True, default_countries=["in", "us", "gb"])

    assert 6 <= len(expanded) <= 10
    for q in expanded:
        assert "site:" not in q.title_keywords.lower()
        assert not any(f in q.title_keywords.lower().split() for f in ["jobs", "hiring", "openings", "fte"])
        assert q.country in ["in", "us", "gb"]

@pytest.mark.asyncio
async def test_per_source_timeouts_are_independent():
    """Test D3: Per-source timeouts are independent; slow source never cancels or starves another."""
    async def fast_source():
        await asyncio.sleep(0.05)
        return [Job(title="Fast Job", company="A", apply_url="https://a.com/1", source="Fast")], "ok", "ok (1 jobs)"

    async def slow_source():
        await asyncio.sleep(0.5)  # will exceed 0.1s timeout
        return [Job(title="Slow Job", company="B", apply_url="https://b.com/2", source="Slow")], "ok", "ok (1 jobs)"

    t_fast = _run_source_safely("Fast", fast_source, timeout_s=0.2)
    t_slow = _run_source_safely("Slow", slow_source, timeout_s=0.1)

    res_fast, res_slow = await asyncio.gather(t_fast, t_slow)

    jobs_fast, st_fast, reason_fast, el_fast = res_fast
    jobs_slow, st_slow, reason_slow, el_slow = res_slow

    # Fast source completed with jobs
    assert st_fast == "ok"
    assert len(jobs_fast) == 1
    # Slow source timed out independently without crashing fast source
    assert st_slow == "timeout"
    assert len(jobs_slow) == 0

def test_funnel_counts_add_up():
    """Test D4: Funnel counts add up correctly across stages."""
    valid_job_1 = Job(title="Job 1", company="Company A", apply_url="https://a.com/1", source="Adzuna")
    valid_job_2 = Job(title="Job 2", company="Company B", apply_url="https://b.com/2", source="JSearch")
    duplicate_job = Job(title="Job 1", company="Company A", apply_url="https://a.com/1", source="Adzuna")
    missing_job = Job(title="", company="", apply_url="", source="Other")

    raws = [
        RawResult(url=j.apply_url, title=j.title or "", text="desc", source_query="q", job=j)
        for j in [valid_job_1, valid_job_2, duplicate_job, missing_job]
    ]

    state = {
        "raw_results": raws,
        "seen_urls": set(),
        "preferences": Preferences(max_age_days=30),
    }

    res = rule_filter(state)
    funnel = res["funnel"]

    assert funnel["fetched"]["total"] == 4
    assert funnel["normalized"]["count"] == 4
    assert funnel["deduped"]["count"] == 3
    assert funnel["deduped"]["dropped"] == 1  # 1 duplicate
    assert funnel["hard_filters"]["passed"] == 2  # job 1 and job 2 passed
    assert funnel["hard_filters"]["dropped"] == 1  # 1 missing fields

def test_no_mock_data_guard_rejects_empty_or_fabricated_jobs():
    """Test D5: No mock data anywhere - validate_job_guard strictly enforces real schema fields."""
    valid = Job(title="Valid Title", company="Acme Corp", apply_url="https://acme.com/jobs/1", source="Greenhouse")
    assert validate_job_guard(valid) is True

    # Missing title
    assert validate_job_guard(Job(title="", company="Acme Corp", apply_url="https://acme.com", source="Adzuna")) is False
    # Missing company
    assert validate_job_guard(Job(title="Dev", company="", apply_url="https://acme.com", source="Adzuna")) is False
    # Missing apply url
    assert validate_job_guard(Job(title="Dev", company="Acme Corp", apply_url="", url="", source="Adzuna")) is False
    # Missing source
    assert validate_job_guard(Job(title="Dev", company="Acme Corp", apply_url="https://acme.com", source="")) is False

from backend.nodes.rule_filter import (
    normalize_url,
    is_non_job_posting,
    is_stale_posting,
    compute_skill_overlap,
    rule_filter,
)
from backend.schemas import RawResult, Profile, Preferences

def test_normalize_url():
    url = "https://Example.com/jobs/dev-1/?utm_source=test#apply"
    norm = normalize_url(url)
    assert norm == "https://example.com/jobs/dev-1"

def test_is_non_job_posting():
    assert is_non_job_posting("https://techblog.com/blog/how-to-prep", "Tips", "Learn how to prepare") is True
    assert is_non_job_posting("https://jobs.com/dev", "Software Engineer", "Requirements: Python, SQL. Salary: 10 LPA") is False

def test_is_stale_posting():
    old_date = "2020-01-01T00:00:00Z"
    recent_date = "2026-10-08T00:00:00Z"
    assert is_stale_posting(old_date, max_age_days=30) is True
    assert is_stale_posting(recent_date, max_age_days=30) is False

def test_compute_skill_overlap():
    top_skills = ["python", "react", "fastapi", "docker"]
    text = "We are seeking a Python and React engineer. Docker experience is a plus."
    score = compute_skill_overlap(top_skills, text)
    assert score == 0.75  # 3 out of 4 matched

def test_rule_filter_pipeline():
    profile = Profile(
        seniority="mid",
        years_experience=2.0,
        top_skills=["python", "fastapi", "react"],
        domains=["web"],
        past_titles=["dev"],
        education="B.Tech",
        target_titles=["full stack"]
    )
    prefs = Preferences(job_types=["fte"], locations=["remote"], sort_by="match")

    raw = [
        RawResult(url="https://site.com/job1", title="Python Dev", text="Python and FastAPI full-time job", source_query="q"),
        RawResult(url="https://site.com/job1?ref=1", title="Python Dev", text="Duplicate URL", source_query="q"),
        RawResult(url="https://blog.com/article", title="Blog", text="Just an article", source_query="q"),
        RawResult(url="https://site.com/irrelevant", title="Cook", text="Chef needed for restaurant", source_query="q"),
    ]

    state = {
        "raw_results": raw,
        "seen_urls": set(),
        "profile": profile,
        "preferences": prefs,
    }

    result = rule_filter(state)
    candidates = result["candidates"]
    assert len(candidates) == 1
    assert candidates[0].url == "https://site.com/job1"

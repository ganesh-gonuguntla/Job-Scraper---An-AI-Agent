from backend.nodes.ranker import apply_ranker
from backend.schemas import ScoredJob, Preferences

def test_ranker_sorting_and_filtering():
    jobs = [
        ScoredJob(idx=0, url="http://1", title="J1", job_type="fte", score=80, salary_annual_inr=1500000.0, posted_date="2026-10-05"),
        ScoredJob(idx=1, url="http://2", title="J2", job_type="fte", score=95, salary_annual_inr=1000000.0, posted_date="2026-10-01"),
        ScoredJob(idx=2, url="http://3", title="J3", job_type="intern", score=90, salary_annual_inr=300000.0, posted_date="2026-10-07"),
        ScoredJob(idx=3, url="http://4", title="J4", job_type="fte", score=85, salary_annual_inr=None, posted_date="2026-10-06"),
    ]

    # Test sort by match for FTE
    prefs_match = Preferences(job_types=["fte"], sort_by="match")
    ranked_match = apply_ranker(jobs, prefs_match)
    assert len(ranked_match) == 3
    assert ranked_match[0].title == "J2"  # score 95

    # Test sort by salary with min salary filter 1,200,000
    prefs_sal = Preferences(job_types=["fte"], min_salary_inr_annual=1200000, sort_by="salary")
    ranked_sal = apply_ranker(jobs, prefs_sal)
    # J2 has 1,000,000 so dropped; J1 has 1,500,000 kept; J4 has None kept
    assert len(ranked_sal) == 2
    assert ranked_sal[0].title == "J1"
    assert ranked_sal[1].title == "J4"

    # Test sort by recency
    prefs_rec = Preferences(job_types=["fte", "intern"], sort_by="recency")
    ranked_rec = apply_ranker(jobs, prefs_rec)
    assert ranked_rec[0].title == "J3"  # 2026-10-07

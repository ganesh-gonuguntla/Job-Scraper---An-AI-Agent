from backend.nodes.extract_jobs import normalize_salary_annual_inr

def test_lpa_annual_normalization():
    res = normalize_salary_annual_inr(6.0, 14.0, "INR", "year")
    assert res == 1400000.0

def test_monthly_stipend_normalization():
    res = normalize_salary_annual_inr(20000.0, 30000.0, "INR", "month")
    assert res == 360000.0

def test_usd_annual_normalization():
    res = normalize_salary_annual_inr(25000.0, 35000.0, "USD", "year", fx_usd_inr=80.0)
    assert res == 2800000.0

def test_unlisted_salary():
    res = normalize_salary_annual_inr(None, None, None, "unknown")
    assert res is None

from backend.nodes.batch_builder import trim_job_text, build_batches, estimate_tokens
from backend.schemas import RawResult

def test_trim_job_text():
    long_text = (
        "About Us\nWe are a happy company.\n\n"
        "Requirements\nMust have 3 years Python and SQL.\n"
        "Responsibilities\nBuild APIs.\n\n"
        "Perks & Benefits\nFree snacks and gym."
    )
    trimmed = trim_job_text(long_text, token_cap=200)
    assert "Requirements" in trimmed
    assert "About Us" not in trimmed

def test_build_batches():
    items = [
        RawResult(url=f"https://job{i}.com", title=f"Job {i}", text="Short requirement text with Python", source_query="q")
        for i in range(12)
    ]
    batches = build_batches(items)
    # Since max 5 per batch, 12 items should be at least 3 batches
    assert len(batches) >= 3
    for b in batches:
        assert len(b) <= 5

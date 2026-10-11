import os
from pathlib import Path
import pytest
from backend.schemas import Job, validate_job_guard
from backend.search import deduplicate_jobs

FORBIDDEN_FAKE_COMPANIES = [
    "TechCorp",
    "CloudScale",
    "NexusTech",
    "Apex Digital",
    "HyperGrow",
    "IndieCorp",
]

def test_repo_has_zero_forbidden_fake_company_names():
    """
    Scans the repository to ensure no mock/fake companies or static job lists exist.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent
    excluded_dirs = {".git", "node_modules", ".pytest_cache", "__pycache__", "dist", "data"}
    excluded_files = {"test_no_fake_data.py"}

    violations = []

    for file_path in root_dir.rglob("*"):
        if file_path.is_dir():
            continue
        # Skip excluded dirs
        if any(part in excluded_dirs for part in file_path.parts):
            continue
        if file_path.name in excluded_files:
            continue
        # Only check text/code files
        if file_path.suffix.lower() not in [".py", ".json", ".js", ".jsx", ".ts", ".tsx", ".md", ".txt", ".html", ".css", ".env"]:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for fake in FORBIDDEN_FAKE_COMPANIES:
                if fake in content:
                    violations.append(f"{file_path.relative_to(root_dir)}: contains forbidden fake name '{fake}'")
        except Exception:
            pass

    assert not violations, f"Forbidden fake company names found in repository:\n" + "\n".join(violations)

def test_job_guard_rejects_missing_fields():
    """
    Enforces that jobs lacking title, company, apply_url or source are strictly rejected.
    """
    # 1. Missing source
    j1 = Job(
        title="Software Engineer",
        company="Real Org Inc",
        apply_url="https://example.org/jobs/123",
        source=""
    )
    assert not validate_job_guard(j1), "Job without source must be rejected"

    # 2. Missing apply_url
    j2 = Job(
        title="Software Engineer",
        company="Real Org Inc",
        apply_url="",
        url="",
        source="Adzuna"
    )
    assert not validate_job_guard(j2), "Job without apply_url must be rejected"

    # 3. Missing company
    j3 = Job(
        title="Software Engineer",
        company="",
        apply_url="https://example.org/jobs/123",
        source="Adzuna"
    )
    assert not validate_job_guard(j3), "Job without company must be rejected"

    # 4. Missing title
    j4 = Job(
        title="",
        company="Real Org Inc",
        apply_url="https://example.org/jobs/123",
        source="Adzuna"
    )
    assert not validate_job_guard(j4), "Job without title must be rejected"

    # 5. Fully qualified real job
    j_valid = Job(
        title="Python Backend Developer",
        company="Real Tech Ltd",
        apply_url="https://company.careers/jobs/456",
        source="Adzuna",
        source_job_id="adz-456",
    )
    assert validate_job_guard(j_valid), "Valid real job must pass guard"

def test_deduplicate_jobs_enforces_guards():
    """
    Tests that deduplicate_jobs filters out invalid items and tracks source counts.
    """
    jobs = [
        Job(
            title="Senior Engineer",
            company="Acme Corp",
            apply_url="https://acme.com/apply/1?utm_source=ad",
            source="Adzuna",
            source_job_id="1"
        ),
        # Duplicate with different UTM tags
        Job(
            title="Senior Engineer",
            company="Acme Corp",
            apply_url="https://acme.com/apply/1?utm_source=diff",
            source="Adzuna",
            source_job_id="1-dup"
        ),
        # Invalid job lacking apply_url
        Job(
            title="Ghost Engineer",
            company="Ghost Corp",
            apply_url="",
            source="Unknown"
        ),
        # Valid Remotive job
        Job(
            title="Frontend Developer",
            company="Remote Studio",
            apply_url="https://remotestudio.com/jobs/fe",
            source="Remotive",
            source_job_id="rem-fe"
        )
    ]

    deduped, counts = deduplicate_jobs(jobs)
    assert len(deduped) == 2, f"Expected 2 unique valid jobs, got {len(deduped)}"
    assert counts["Adzuna"] == 2
    assert counts["Remotive"] == 1
    assert counts["deduped"] == 2
    assert all(j.source in ["Adzuna", "Remotive"] for j in deduped)
    assert all(j.apply_url.startswith("http") for j in deduped)

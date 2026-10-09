import operator
from typing import Annotated, TypedDict
from backend.schemas import (
    Preferences,
    Profile,
    SearchQuery,
    RawResult,
    Job,
    ScoredJob,
)

class GraphState(TypedDict):
    # Inputs
    run_id: str
    pdf_bytes: bytes
    preferences: Preferences

    # Pipeline data
    resume_text: str
    resume_hash: str
    profile: Profile | None
    queries: list[SearchQuery]
    raw_results: Annotated[list[RawResult], operator.add]
    seen_urls: set[str]
    candidates: list[RawResult]
    batches: list[list[RawResult]]
    jobs: list[Job]
    scored_jobs: list[ScoredJob]
    final_jobs: list[ScoredJob]

    # Control
    retry_count: int
    gate_passed: bool
    status_note: str | None
    errors: Annotated[list[str], operator.add]

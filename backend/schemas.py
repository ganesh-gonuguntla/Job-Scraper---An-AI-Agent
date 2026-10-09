from typing import Literal
from pydantic import BaseModel, Field

class Preferences(BaseModel):
    job_types: list[Literal["intern", "fte", "contract", "part_time"]] = Field(
        default=["fte", "intern"],
        description="Job types desired by the user"
    )
    min_salary_inr_annual: int | None = Field(
        default=None,
        description="Minimum annual salary in INR"
    )
    locations: list[str] = Field(
        default_factory=lambda: ["India", "remote"],
        description="Locations to search for, can include 'remote'"
    )
    sort_by: Literal["match", "salary", "recency"] = Field(
        default="match",
        description="Primary sorting priority"
    )
    max_age_days: int = Field(
        default=30,
        description="Max job posting age in days"
    )

class Profile(BaseModel):
    seniority: Literal["student", "entry", "mid", "senior", "lead"]
    years_experience: float
    top_skills: list[str] = Field(description="Ranked, max 12, lowercase")
    domains: list[str] = Field(description="Max 5 industry/tech domains")
    past_titles: list[str] = Field(description="Max 4 past titles")
    education: str = Field(description="One line summary")
    location: str | None = None
    target_titles: list[str] = Field(description="Max 3, inferred, plausible")

class SearchQuery(BaseModel):
    q: str = Field(description="Max 12 words")
    angle: Literal["exact_title", "adjacent_title", "skill_stack", "site_targeted"]
    site: str | None = None

class ProfileAndQueries(BaseModel):
    profile: Profile
    queries: list[SearchQuery] = Field(description="Max 5 queries")

class RawResult(BaseModel):
    url: str
    title: str
    text: str
    published: str | None = None
    source_query: str
    rule_score: float = 0.0

class Job(BaseModel):
    idx: int
    is_real_posting: bool = True
    title: str | None = None
    company: str | None = None
    location: str | None = None
    remote: bool | None = None
    job_type: Literal["intern", "fte", "contract", "part_time", "unknown"] = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: Literal["year", "month", "unknown"] = "unknown"
    skills_required: list[str] = Field(default_factory=list, description="Max 10 skills")
    experience_years_min: float | None = None
    posted_date: str | None = None

class JobBatch(BaseModel):
    jobs: list[Job]

class Score(BaseModel):
    idx: int
    score: int = Field(ge=0, le=100)
    reason: str = Field(description="Max 20 words")
    matched_skills: list[str] = Field(default_factory=list, description="Max 5")
    missing_skills: list[str] = Field(default_factory=list, description="Max 3")

class ScoreBatch(BaseModel):
    scores: list[Score]

class RefinerOutput(BaseModel):
    diagnosis: str = Field(description="One sentence failure diagnosis")
    queries: list[SearchQuery] = Field(description="Max 4 new queries")

class ScoredJob(BaseModel):
    # Job fields
    idx: int
    is_real_posting: bool = True
    title: str | None = None
    company: str | None = None
    location: str | None = None
    remote: bool | None = None
    job_type: Literal["intern", "fte", "contract", "part_time", "unknown"] = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: Literal["year", "month", "unknown"] = "unknown"
    skills_required: list[str] = Field(default_factory=list)
    experience_years_min: float | None = None
    posted_date: str | None = None
    # Score fields
    score: int = 0
    reason: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    # Metadata fields
    url: str
    salary_annual_inr: float | None = None
    rule_score: float = 0.0

from typing import Literal, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator

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

import re

FILLER_WORDS_REGEX = re.compile(
    r"\b(jobs?|hiring|openings?|fte|full[\s-]?time|careers?|positions?|roles?|vacanc(?:y|ies))\b",
    re.IGNORECASE
)
SITE_OPERATOR_REGEX = re.compile(r"site:[^\s]+", re.IGNORECASE)

class SearchQuery(BaseModel):
    title_keywords: str = Field(
        default="",
        description="Target role title keywords without filler words (e.g. 'Data Analyst', 'Power BI Developer')"
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Core skills for this query"
    )
    location: str | None = Field(
        default=None,
        description="City or specific place name if specified, never 'Worldwide' or 'Remote'"
    )
    country: str = Field(
        default="in",
        description="2-letter ISO country code e.g. in, us, gb"
    )
    remote: bool = Field(
        default=False,
        description="True if remote / work from home"
    )
    employment_type: Literal["fulltime", "contractor", "parttime", "intern", "any"] = Field(
        default="any",
        description="OpenWeb Ninja employment type filter"
    )
    date_posted: str | None = Field(
        default="month",
        description="Date posted window: today, 3days, week, month, all"
    )
    angle: str = "exact_title"

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def sanitize_and_normalize(cls, data: Any) -> Any:
        if isinstance(data, str):
            data = {"title_keywords": data}
        if not isinstance(data, dict):
            return data

        # Normalize angle and employment_type
        raw_angle = str(data.get("angle") or "exact_title").lower().strip()
        allowed_angles = ["exact_title", "adjacent_title", "skill_stack", "entry_level", "internship"]
        data["angle"] = raw_angle if raw_angle in allowed_angles else "exact_title"

        raw_emp = str(data.get("employment_type") or "any").lower().strip()
        allowed_emps = ["fulltime", "contractor", "parttime", "intern", "any"]
        data["employment_type"] = raw_emp if raw_emp in allowed_emps else "any"

        # Backwards compatibility: if 'q' was provided instead of title_keywords
        raw_title = data.get("title_keywords") or data.get("q") or ""

        # 1. Remove site: operators
        cleaned_title = SITE_OPERATOR_REGEX.sub("", raw_title)

        # 2. Detect remote keyword in title and strip it
        is_remote = bool(data.get("remote", False))
        if re.search(r"\bremote\b", cleaned_title, re.IGNORECASE):
            is_remote = True
            cleaned_title = re.sub(r"\bremote\b", "", cleaned_title, flags=re.IGNORECASE)

        # 3. Strip all filler words
        cleaned_title = FILLER_WORDS_REGEX.sub("", cleaned_title)

        # 4. Clean punctuation and excess whitespace
        cleaned_title = re.sub(r"[^\w\s\+\#\./\-]", " ", cleaned_title)
        cleaned_title = re.sub(r"\s+", " ", cleaned_title).strip()

        # 5. Sanitize location: never allow 'Worldwide', 'Remote', 'Any', etc.
        raw_loc = data.get("location")
        if raw_loc:
            loc_lower = str(raw_loc).strip().lower()
            if loc_lower in ["worldwide", "remote", "any", "global", "all", "anywhere"]:
                data["location"] = None
                is_remote = True
            else:
                data["location"] = str(raw_loc).strip()

        data["title_keywords"] = cleaned_title
        data["remote"] = is_remote

        # Normalize country to 2-letter lower
        raw_country = data.get("country", "in")
        if raw_country and len(str(raw_country).strip()) == 2:
            data["country"] = str(raw_country).strip().lower()
        else:
            data["country"] = "in"

        return data

    @property
    def q(self) -> str:
        """Structured string representation for display and fallback text queries."""
        parts = [self.title_keywords]
        if self.skills:
            parts.append(" ".join(self.skills[:2]))
        if self.location:
            parts.append(f"in {self.location}")
        elif self.remote:
            parts.append("(Remote)")
        return " ".join(parts).strip()

    def render_adzuna_what_or(self) -> str:
        """
        Adzuna what_or query: 2-4 focused keywords per query (title words plus skills).
        No stop words or filler words.
        """
        words = [w for w in re.sub(r"[^\w\+\#\.]", " ", self.title_keywords).split() if len(w) > 1]
        for s in self.skills:
            for sw in s.split():
                if sw.lower() not in [w.lower() for w in words]:
                    words.append(sw)
        # 2 to 4 focused keywords
        return " ".join(words[:4]) if words else self.title_keywords

    def render_jsearch_query(self) -> Tuple[str, str, bool]:
        """
        JSearch query: natural text '<title> in <place>' plus country parameter,
        and remote flag for work_from_home=true.
        """
        place = self.location if (self.location and self.location.lower() not in ["any", "worldwide", "remote", "global"]) else None
        q_str = f"{self.title_keywords} in {place}" if place else self.title_keywords
        return q_str.strip(), self.country, self.remote

class ProfileAndQueries(BaseModel):
    profile: Profile
    queries: list[SearchQuery] = Field(description="6-10 targeted queries", min_length=1)

class RawResult(BaseModel):
    url: str
    title: str
    text: str
    published: str | None = None
    source_query: str
    rule_score: float = 0.0
    job: Any = None

from datetime import datetime, timezone
from pydantic import model_validator

class Job(BaseModel):
    idx: int = 0
    url: str = ""
    apply_url: str = ""
    source: str = ""
    source_job_id: str = ""
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_payload: Any = None
    is_real_posting: bool = True
    title: str | None = None
    company: str | None = Field(default=None, alias="company_name")
    location: str | None = "Not Specified"
    remote: bool | None = Field(default=None, alias="remote_status")
    job_type: Literal["intern", "fte", "contract", "part_time", "unknown"] | None = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: Literal["year", "month", "unknown"] | None = "unknown"
    salary_is_predicted: bool = False
    skills_required: list[str] = Field(default_factory=list, description="Max 10 skills")
    experience_years_min: float | None = None
    posted_date: str | None = None
    description: str | None = None
    description_is_partial: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("salary_period", mode="before")
    @classmethod
    def normalize_salary_period(cls, v: Any) -> str:
        if not v or not isinstance(v, str):
            return "unknown"
        v_low = v.lower().strip()
        if v_low in ("year", "month"):
            return v_low
        return "unknown"

    @model_validator(mode="after")
    def sync_urls(self) -> "Job":
        if not self.apply_url and self.url:
            self.apply_url = self.url
        elif not self.url and self.apply_url:
            self.url = self.apply_url
        return self

def validate_job_guard(job: Job) -> bool:
    """
    Enforces no fake data:
    Rejects any job missing title, company, apply_url, or source.
    """
    if not job.title or not job.title.strip():
        return False
    if not job.company or not job.company.strip():
        return False
    apply_target = job.apply_url or job.url
    if not apply_target or not apply_target.strip() or not apply_target.startswith("http"):
        return False
    if not job.source or not job.source.strip():
        return False
    return True

class JobBatch(BaseModel):
    jobs: list[Job] = Field(default_factory=list)

    @classmethod
    def model_validate(cls, obj: Any, *args, **kwargs):
        if isinstance(obj, list):
            obj = {"jobs": obj}
        return super().model_validate(obj, *args, **kwargs)

class Score(BaseModel):
    idx: int = 0
    score: int = Field(default=50, ge=0, le=100)
    reason: str = Field(default="Candidate matches core stack requirements", description="Summary reason in 15-25 words")
    matched_skills: list[str] = Field(default_factory=list, description="Max 6 matching skills")
    missing_skills: list[str] = Field(default_factory=list, description="Max 3 missing or gap skills")
    why_fit: list[str] = Field(default_factory=list, description="2-3 concise bullet points on why the candidate is a match")
    interview_tip: str | None = Field(default=None, description="Actionable technical interview tip for this position")

class ScoreBatch(BaseModel):
    scores: list[Score] = Field(default_factory=list)

    @classmethod
    def model_validate(cls, obj: Any, *args, **kwargs):
        if isinstance(obj, list):
            obj = {"scores": obj}
        return super().model_validate(obj, *args, **kwargs)

class RefinerOutput(BaseModel):
    diagnosis: str = Field(default="Refining search queries.", description="One sentence failure diagnosis")
    queries: list[SearchQuery] = Field(default_factory=list, description="Max 4 new queries", alias="new_queries")

    model_config = ConfigDict(populate_by_name=True)

class ScoredJob(BaseModel):
    # Job fields
    idx: int
    is_real_posting: bool = True
    title: str | None = None
    company: str | None = None
    location: str | None = "Not Specified"
    remote: bool | None = None
    job_type: Literal["intern", "fte", "contract", "part_time", "unknown"] = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: Literal["year", "month", "unknown"] = "unknown"
    salary_is_predicted: bool = False
    skills_required: list[str] = Field(default_factory=list)
    experience_years_min: float | None = None
    posted_date: str | None = None
    description: str | None = None
    description_is_partial: bool = False
    # Score fields
    score: int = 0
    reason: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    why_fit: list[str] = Field(default_factory=list)
    interview_tip: str | None = None
    # Real Source Tracking Metadata fields
    url: str = ""
    apply_url: str = ""
    source: str = ""
    source_job_id: str = ""
    fetched_at: str = ""
    raw_payload: Any = None
    salary_annual_inr: float | None = None
    rule_score: float = 0.0

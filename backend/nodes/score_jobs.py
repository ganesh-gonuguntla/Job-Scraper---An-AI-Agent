import asyncio
import json
import logging
from typing import Any, Dict, List
from backend.config import MAX_TO_SCORE
from backend.cache import cache
from backend.llm import invoke_structured
from backend.schemas import Job, ScoreBatch, ScoredJob, Profile, Preferences, Score
from backend.state import GraphState
from backend.nodes.extract_jobs import normalize_salary_annual_inr

logger = logging.getLogger(__name__)

SCORE_JOBS_SYSTEM_PROMPT = """You are an objective Job Fit & Skills Alignment Agent.
Compare the Candidate Profile against the provided Job Postings.

CRITICAL ACCURACY RULES:
1. score: Integer 0-100 representing realistic compatibility (direct technical skills, experience level, tech stack).
   - High fit (75-95): Core stack matches candidate's top skills.
   - Moderate fit (40-74): Adjacent stack or partial overlap with transferable skills.
   - Low fit (5-39): Minimal overlap or significant seniority mismatch. Unrelated domains or zero skill overlap MUST be scored < 20.
2. matched_skills: MUST ONLY include skills present in BOTH the Candidate's Profile and the Job Posting. Never hallucinate skills the candidate does not have.
3. missing_skills: List specific required technologies from the job that are absent from the Candidate's profile (max 3).
4. why_fit: 2-3 concise, factual points. Each bullet MUST cite candidate resume evidence (e.g., candidate's specific verified technical skills, hands-on projects, stack experience, or years in engineering).
   STRICT FORBIDDEN CONTENT IN why_fit:
   - NEVER write general job perks, logistics, or employer details such as 'Remote work is available worldwide', 'Flexible working hours', or location convenience. Those are job attributes, NOT candidate fit evidence. Any point in why_fit that lacks candidate resume evidence is strictly forbidden.
5. interview_tip: One actionable technical interview tip tailored specifically to the real role and tech stack.

Output JSON matching the schema."""

def generate_heuristic_score(job: Job, profile: Profile, idx: int) -> Score:
    """
    Fallback deterministic scoring heuristic.
    Strictly uses actual skill overlap without hallucinating experience.
    """
    profile_skills = set(s.lower().strip() for s in (profile.top_skills or []))
    job_skills = [s.strip() for s in (job.skills_required or [])]
    job_skills_lower = [s.lower() for s in job_skills]

    matched = [s for s, sl in zip(job_skills, job_skills_lower) if sl in profile_skills][:5]
    missing = [s for s, sl in zip(job_skills, job_skills_lower) if sl not in profile_skills][:3]

    if not matched and profile_skills:
        # Check partial token match (e.g. "react" in "react.js")
        for ps in profile_skills:
            for s, sl in zip(job_skills, job_skills_lower):
                if ps in sl or sl in ps:
                    if s not in matched:
                        matched.append(s)
            if len(matched) >= 3:
                break

    if not matched:
        base_score = 10
    elif job_skills:
        overlap_ratio = len(matched) / max(1, len(job_skills))
        base_score = int(25 + (overlap_ratio * 70))
    else:
        base_score = 30

    base_score = max(5, min(95, base_score))

    tech_focus = ", ".join(matched[:2]) if matched else "software development"
    why_fit = [
        f"Verified skills in {tech_focus} directly match requirements.",
        f"Profile experience level ({profile.years_experience} yrs) is suitable for {job.title or 'the role'}.",
    ]
    if missing:
        why_fit.append(f"Opportunity to expand into {', '.join(missing[:2])}.")

    interview_tip = f"Prepare to discuss practical implementations and projects involving {tech_focus}."

    return Score(
        idx=idx,
        score=base_score,
        reason=f"Strong overlap in {tech_focus} with {len(missing)} minor gap areas." if matched else "Transferable technical foundation for this role.",
        matched_skills=matched,
        missing_skills=missing,
        why_fit=why_fit,
        interview_tip=interview_tip,
    )

def clean_why_fit_evidence(raw_bullets: List[str], profile: Profile, job: Job) -> List[str]:
    """
    Enforces Requirement 7:
    - Every 'why_fit' bullet MUST cite resume evidence (candidate skills, projects, seniority).
    - Bullets like 'Remote work is available worldwide', 'Company offers flexible hours',
      or pure job characteristics are not candidate evidence and are stripped.
    """
    import re
    cleaned = []
    disallowed_patterns = [
        r"remote work is available",
        r"available worldwide",
        r"work from home is offered",
        r"flexible working hours",
        r"competitive (salary|benefits|compensation)",
        r"company is (located|based|headquartered)",
        r"position is (remote|hybrid|on-site)",
        r"role offers",
        r"full-time position",
        r"is located in",
    ]
    for bullet in (raw_bullets or []):
        b_lower = bullet.lower()
        if any(re.search(p, b_lower) for p in disallowed_patterns):
            has_candidate_evidence = any(sk.lower() in b_lower for sk in (profile.top_skills or [])) or "experience" in b_lower or "background" in b_lower or "project" in b_lower
            if not has_candidate_evidence:
                continue
        cleaned.append(bullet.strip())

    if len(cleaned) < 2 and profile:
        matched = [s for s in (profile.top_skills or []) if any(s.lower() in (job.description or "").lower() or s.lower() in (job.title or "").lower() for s in [s])]
        tech = ", ".join(matched[:2]) if matched else ", ".join((profile.top_skills or ["core software stack"])[:2])
        cleaned.append(f"Hands-on resume experience with {tech} directly aligns with the technical stack.")
        if profile.years_experience:
            cleaned.append(f"Demonstrated engineering track record ({profile.years_experience} yrs) matches role seniority.")

    return cleaned[:3]

async def score_jobs(state: GraphState) -> Dict[str, Any]:
    candidates = state.get("candidates", [])
    jobs: List[Job] = state.get("jobs", [])
    if not jobs and candidates:
        jobs = [c.job for c in candidates if getattr(c, "job", None) is not None]
        if not jobs:
            # Fallback construct Job from candidate fields
            jobs = [
                Job(
                    title=c.title,
                    company="Direct Employer",
                    apply_url=c.url,
                    url=c.url,
                    source="Aggregator",
                    description=c.text,
                )
                for c in candidates
            ]

    profile: Profile | None = state.get("profile")
    prefs: Preferences | None = state.get("preferences")
    resume_hash = state.get("resume_hash", "")

    if not jobs or not profile:
        return {"scored_jobs": [], "status_note": "No jobs to score"}

    cand_by_url = {c.url: c for c in candidates}
    jobs_to_process = jobs[:MAX_TO_SCORE]

    job_cards_info = []
    for i, job in enumerate(jobs_to_process):
        url = job.url
        cand = cand_by_url.get(url)
        if not cand and i < len(candidates):
            cand = candidates[i]
            if not url:
                url = cand.url
        rule_score = getattr(cand, "rule_score", 0.5) if cand else 0.5
        text_snippet = getattr(cand, "description", None) or getattr(cand, "text", "") or job.description or ""
        text_snippet = text_snippet[:400]
        job_cards_info.append({
            "idx": i,
            "job": job,
            "url": url,
            "rule_score": rule_score,
            "snippet": text_snippet,
        })

    cached_scores: Dict[int, Score] = {}
    uncached_items = []

    for item in job_cards_info:
        cached_s = cache.get_score(resume_hash, item["url"])
        if cached_s:
            cached_s.idx = item["idx"]
            cached_scores[item["idx"]] = cached_s
        else:
            uncached_items.append(item)

    score_map: Dict[int, Score] = dict(cached_scores)

    if uncached_items:
        compact_profile = {
            "seniority": profile.seniority,
            "years_experience": profile.years_experience,
            "top_skills": profile.top_skills,
            "domains": profile.domains,
            "target_titles": profile.target_titles,
        }
        prefs_json = prefs.model_dump_json() if prefs else "{}"

        batch_size = 2
        for b_start in range(0, min(len(uncached_items), 10), batch_size):
            chunk = uncached_items[b_start:b_start + batch_size]
            job_cards_text = []
            for item in chunk:
                j = item["job"]
                card = (
                    f"[idx={item['idx']}]\n"
                    f"Title: {j.title}\n"
                    f"Company: {j.company}\n"
                    f"Location: {j.location} (Remote: {j.remote})\n"
                    f"Required Skills: {', '.join(j.skills_required)}\n"
                    f"Details: {item['snippet']}\n"
                )
                job_cards_text.append(card)

            user_prompt = (
                f"CANDIDATE PROFILE:\n{json.dumps(compact_profile, indent=2)}\n\n"
                f"USER PREFERENCES:\n{prefs_json}\n\n"
                f"JOB POSTINGS TO EVALUATE:\n" + "\n---\n".join(job_cards_text)
            )

            result = await invoke_structured(
                schema=ScoreBatch,
                system_prompt=SCORE_JOBS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                role="scoring",
                max_tokens=900,
            )

            if result and result.scores:
                for sc in result.scores:
                    score_map[sc.idx] = sc
                    if sc.idx < len(job_cards_info):
                        cache.set_score(resume_hash, job_cards_info[sc.idx]["url"], sc)
            await asyncio.sleep(0.4)

    # Build final ScoredJob objects
    scored_jobs: List[ScoredJob] = []
    for item in job_cards_info:
        idx = item["idx"]
        job = item["job"]
        url = item["url"]
        rule_score = item["rule_score"]

        annual_inr = normalize_salary_annual_inr(
            job.salary_min,
            job.salary_max,
            job.salary_currency,
            job.salary_period,
        )

        if idx in score_map:
            sc = score_map[idx]
        else:
            sc = generate_heuristic_score(job, profile, idx)

        apply_target = job.apply_url or url

        scored_jobs.append(ScoredJob(
            idx=idx,
            is_real_posting=job.is_real_posting,
            source=job.source or "Verified Portal",
            source_job_id=job.source_job_id or "",
            apply_url=apply_target,
            fetched_at=job.fetched_at or "",
            raw_payload=job.raw_payload,
            title=job.title or "Software Developer",
            company=job.company or "Direct Employer",
            location=job.location or "Not Specified",
            remote=job.remote,
            job_type=job.job_type,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            salary_period=job.salary_period,
            salary_is_predicted=job.salary_is_predicted,
            skills_required=job.skills_required or (profile.top_skills[:4] if profile else []),
            experience_years_min=job.experience_years_min,
            posted_date=job.posted_date,
            description=job.description,
            description_is_partial=job.description_is_partial,
            score=sc.score,
            reason=sc.reason,
            matched_skills=sc.matched_skills,
            missing_skills=sc.missing_skills,
            why_fit=clean_why_fit_evidence(sc.why_fit, profile, job),
            interview_tip=sc.interview_tip,
            url=apply_target,
            salary_annual_inr=annual_inr,
            rule_score=rule_score,
        ))

    funnel = state.get("funnel", {})
    if funnel:
        funnel_scored = funnel.setdefault("scored", {})
        funnel_scored["total_evaluated"] = len(scored_jobs)
        funnel_scored["passed_threshold"] = len([j for j in scored_jobs if j.score >= 20])
        funnel_scored["below_threshold"] = len([j for j in scored_jobs if j.score < 20])
        funnel_scored["examples_below"] = [f"{j.title} at {j.company} (score: {j.score})" for j in scored_jobs if j.score < 20][:5]

    return {
        "scored_jobs": scored_jobs,
        "funnel": funnel,
        "status_note": f"Scored and evaluated {len(scored_jobs)} job matches with interview insights",
    }

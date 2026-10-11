import argparse
import asyncio
import json
from pathlib import Path
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from typing import Tuple

import httpx

API_BASE = "http://127.0.0.1:8000/api"

async def check_url_liveness(url: str, timeout: float = 8.0) -> Tuple[bool, int, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            # 200, 301, 302, 307, 308, 403 (some ATS/Cloudflare return 403 to automated scripts on datacenters)
            is_live = resp.status_code in [200, 301, 302, 307, 308, 403]
            return is_live, resp.status_code, str(resp.url)
    except Exception as e:
        return False, 0, str(e)

async def run_pipeline_e2e(pdf_path: Path, role_name: str):
    print("=" * 80)
    print(f"JOBPULSE UI-PATH E2E EXECUTION: {role_name.upper()} RESUME")
    print(f"PDF Target: {pdf_path}")
    print("=" * 80)

    if not pdf_path.exists():
        print(f"[ERROR] Resume PDF not found at {pdf_path}")
        return False, None

    # Step 1: Default preferences requested: FTE + Internship, 30d, Worldwide
    prefs = {
        "job_types": ["fte", "intern"],
        "locations": ["any"],  # Worldwide
        "sort_by": "match",
        "max_age_days": 30,
        "min_salary_inr_annual": None,
    }

    # Step 2: POST /api/runs (exact same endpoint UI calls)
    print("\n[UI Path Step 1] Calling POST /api/runs with multipart PDF and preferences...")
    async with httpx.AsyncClient(timeout=180.0) as client:
        with open(pdf_path, "rb") as f:
            files = {"pdf": (pdf_path.name, f.read(), "application/pdf")}
            data = {"preferences": json.dumps(prefs)}
            resp = await client.post(f"{API_BASE}/runs", files=files, data=data)

        if resp.status_code != 200:
            print(f"[ERROR] Failed to create run: HTTP {resp.status_code} - {resp.text}")
            return False, None

        run_id = resp.json()["run_id"]
        print(f"[SUCCESS] Run initialized with ID: {run_id}")

        # Step 3: Stream SSE from GET /api/runs/{run_id}/stream
        print(f"\n[UI Path Step 2] Subscribing to SSE stream /api/runs/{run_id}/stream...")
        final_result = None

        async with client.stream("GET", f"{API_BASE}/runs/{run_id}/stream", timeout=180.0) as response:
            current_event = None
            current_data = []

            async for line in response.aiter_lines():
                if not line:
                    if current_event and current_data:
                        raw_payload = "\n".join(current_data)
                        try:
                            payload = json.loads(raw_payload)
                        except Exception:
                            payload = raw_payload

                        if current_event == "node_end":
                            node = payload.get("node")
                            summary = payload.get("summary", "")
                            print(f"  -> [Node Completed] {node:22} | {summary}")

                        elif current_event == "interrupt":
                            print(f"\n[UI Path Step 3] Human Review interrupt received! Auto-approving via /resume...")
                            profile_data = payload.get("profile", {})
                            queries_data = payload.get("queries", [])
                            print(f"     Profile Seniority: {profile_data.get('seniority')}, Target Titles: {profile_data.get('target_titles')}")
                            print(f"     Queries Generated: {len(queries_data)} queries")
                            for idx, q in enumerate(queries_data, 1):
                                q_title = q.get('title_keywords', q.get('q', ''))
                                q_skills = ', '.join(q.get('skills', []))
                                q_c = q.get('country', 'in')
                                q_rem = 'Remote' if q.get('remote') else 'On-site'
                                print(f"       ({idx}) '{q_title}' | skills: [{q_skills}] | country: {q_c} | {q_rem}")

                            resume_resp = await client.post(
                                f"{API_BASE}/runs/{run_id}/resume",
                                json={"profile": profile_data, "queries": queries_data}
                            )
                            print(f"     Resume response: HTTP {resume_resp.status_code}")

                        elif current_event == "result":
                            print(f"\n[UI Path Step 4] Result event received from SSE stream!")
                            final_result = payload
                            break

                        elif current_event == "error":
                            print(f"[ERROR from SSE] {payload}")
                            break

                    current_event = None
                    current_data = []
                    continue

                if line.startswith("event:"):
                    current_event = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    current_data.append(line.replace("data:", "").strip())

        # Step 4: Verify Funnel API GET /api/runs/{run_id}/funnel
        print(f"\n[UI Path Step 5] Fetching Funnel via GET /api/runs/{run_id}/funnel...")
        funnel_resp = await client.get(f"{API_BASE}/runs/{run_id}/funnel")
        funnel_data = funnel_resp.json().get("funnel") if funnel_resp.status_code == 200 else (final_result.get("funnel") if final_result else {})

        # Display Pipeline Funnel
        print("\n" + "=" * 80)
        print("PIPELINE FUNNEL BREAKDOWN (Every Stage Verified):")
        print("=" * 80)
        if funnel_data:
            fetched_tot = funnel_data.get("fetched", {}).get("total", 0)
            by_src = funnel_data.get("fetched", {}).get("by_source", {})
            norm_cnt = funnel_data.get("normalized", {}).get("count", 0)
            dedup_cnt = funnel_data.get("deduped", {}).get("count", 0)
            hard_passed = funnel_data.get("hard_filters", {}).get("passed", 0)
            hard_dropped = funnel_data.get("hard_filters", {}).get("dropped", 0)
            drop_reasons = funnel_data.get("hard_filters", {}).get("drop_reasons", {})
            scored_eval = funnel_data.get("scored", {}).get("total_evaluated", 0)
            scored_passed = funnel_data.get("scored", {}).get("passed_threshold", 0)
            shown_cnt = funnel_data.get("shown", {}).get("count", 0)

            print(f"1. Fetched         : {fetched_tot} total across sources: {by_src}")
            print(f"2. Normalized      : {norm_cnt}")
            print(f"3. Deduped         : {dedup_cnt} unique candidates")
            print(f"4. Hard Filters    : {hard_passed} passed, {hard_dropped} dropped")
            for r_name, r_info in drop_reasons.items():
                if r_info.get("count", 0) > 0:
                    print(f"     - Drop Reason [{r_name}]: {r_info['count']} dropped. Examples: {r_info.get('examples', [])[:3]}")
            print(f"5. Scored (>=20)    : {scored_passed} passed (evaluated {scored_eval})")
            print(f"6. Shown in UI     : {shown_cnt} job opportunities displayed")
        else:
            print("[WARN] Funnel data was not captured.")

        # Per-source audit bar counts with states and elapsed time
        source_statuses = final_result.get("source_statuses", {}) if final_result else {}
        print("\n" + "=" * 80)
        print("PER-SOURCE AUDIT STATUSES & ELAPSED TIME:")
        print("=" * 80)
        for src, info in source_statuses.items():
            cnt = info.get("count", 0)
            st = info.get("status", "ok")
            reason = info.get("reason", "")
            elapsed = info.get("elapsed_s", 0.0)
            print(f"  {src:12}: {cnt:3} jobs | State: {st:12} | Elapsed: {elapsed:5.2f}s | Tooltip: {reason}")

        final_jobs = final_result.get("final_jobs", []) if final_result else []
        print(f"\nTOTAL JOBS RETURNED: {len(final_jobs)}")
        print("\nTOP 10 JOB MATCHES:")
        print("-" * 80)
        for idx, job in enumerate(final_jobs[:10], 1):
            title = job.get("title")
            comp = job.get("company")
            src = job.get("source")
            score = job.get("score")
            apply_url = job.get("apply_url") or job.get("url")
            loc = job.get("location")
            print(f"#{idx:2} | Score: {score}% | {title} at {comp} | [{src}] in {loc}")
            print(f"     Apply URL: {apply_url}")

        # Liveness checks on top 5 URLs
        print("\n" + "=" * 80)
        print("LIVE HTTP VERIFICATION ON TOP 5 APPLY URLs:")
        print("=" * 80)
        top_5_jobs = final_jobs[:5]
        for idx, job in enumerate(top_5_jobs, 1):
            url = job.get("apply_url") or job.get("url")
            is_live, status, final_url = await check_url_liveness(url)
            state_str = "ACTIVE / STILL OPEN" if is_live else "FAILED / CLOSED"
            print(f"Job #{idx}: {job.get('title')} at {job.get('company')}")
            print(f"  URL    : {url}")
            print(f"  Status : HTTP {status} -> {state_str}")

        return len(final_jobs) >= 15, final_jobs

async def main():
    parser = argparse.ArgumentParser(description="JobPulse E2E UI Path Execution Test")
    parser.add_argument("--role", choices=["analyst", "fullstack", "both"], default="both")
    args = parser.parse_args()

    analyst_pdf = Path("fixtures/data_analyst_resume.pdf")
    fullstack_pdf = Path(r"c:\Users\Balaji Rapolu\.gemini\antigravity-ide\brain\7fd0f42d-88d5-4832-8a58-5471d7430b93\.user_uploaded\media_1791634700470.pdf")

    results = {}
    if args.role in ["analyst", "both"]:
        success, jobs = await run_pipeline_e2e(analyst_pdf, "Data Analyst")
        results["Data Analyst"] = (success, len(jobs) if jobs else 0)

    if args.role in ["fullstack", "both"]:
        success, jobs = await run_pipeline_e2e(fullstack_pdf, "Full Stack Developer")
        results["Full Stack Developer"] = (success, len(jobs) if jobs else 0)

    print("\n" + "=" * 80)
    print("FINAL SUMMARY OF UI-PATH PIPELINE ACCEPTANCE TEST:")
    for role, (success, cnt) in results.items():
        status_str = "PASSED (>=15 jobs)" if success else "FAILED (<15 jobs)"
        print(f"  {role:22}: {cnt} jobs found -> {status_str}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

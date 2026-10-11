import os
import sys
from pathlib import Path
import asyncio
import httpx
from dotenv import load_dotenv

# Ensure root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

from backend.config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    OPENWEBNINJA_API_KEY,
    JSEARCH_BASE_URL,
    log_config_startup,
)
from backend.schemas import Preferences, SearchQuery
from backend.sources.adzuna import search_adzuna
from backend.sources.jsearch import search_jsearch
from backend.sources.boards import search_remotive, search_arbeitnow, search_greenhouse

async def run_adzuna_check():
    print("\n" + "=" * 65)
    print("SOURCE: Adzuna (api.adzuna.com)")
    print("=" * 65)
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("[FAIL] Missing ADZUNA_APP_ID or ADZUNA_APP_KEY in .env")
        return False, 0, []

    prefs = Preferences(locations=["India"], max_age_days=30)
    jobs, status, reason = await search_adzuna("python react developer", prefs, max_results_total=10)
    print(f"Status State : {status}")
    print(f"Status Detail: {reason}")
    print(f"Jobs Returned: {len(jobs)}")
    for i, j in enumerate(jobs[:3], 1):
        print(f"  [{i}] Title    : {j.title}")
        print(f"      Company  : {j.company}")
        print(f"      Location : {j.location}")
        print(f"      Apply URL: {j.apply_url}")
    return bool(jobs or status == "ok"), len(jobs), jobs[:3]

async def run_jsearch_check():
    print("\n" + "=" * 65)
    print("SOURCE: JSearch via OpenWeb Ninja (/search-v2)")
    print("=" * 65)
    if not OPENWEBNINJA_API_KEY:
        print("[FAIL] Missing OPENWEBNINJA_API_KEY in .env")
        return False, 0, []

    prefs = Preferences(locations=["India"], max_age_days=30)
    jobs, status, reason = await search_jsearch("developer jobs in bangalore", prefs, max_results=10)
    print(f"Status State : {status}")
    print(f"Status Detail: {reason}")
    print(f"Jobs Returned: {len(jobs)}")
    for i, j in enumerate(jobs[:3], 1):
        print(f"  [{i}] Title    : {j.title}")
        print(f"      Company  : {j.company}")
        print(f"      Location : {j.location}")
        print(f"      Apply URL: {j.apply_url}")
    return bool(jobs), len(jobs), jobs[:3]

async def run_remotive_check():
    print("\n" + "=" * 65)
    print("SOURCE: Remotive (remotive.com)")
    print("=" * 65)
    jobs, status, reason = await search_remotive("python", max_results=5)
    print(f"Status State : {status}")
    print(f"Status Detail: {reason}")
    print(f"Jobs Returned: {len(jobs)}")
    for i, j in enumerate(jobs[:3], 1):
        print(f"  [{i}] Title    : {j.title}")
        print(f"      Company  : {j.company}")
        print(f"      Apply URL: {j.apply_url}")
    return bool(jobs), len(jobs), jobs[:3]

async def run_arbeitnow_check():
    print("\n" + "=" * 65)
    print("SOURCE: Arbeitnow (arbeitnow.com)")
    print("=" * 65)
    jobs, status, reason = await search_arbeitnow("python", max_results=5)
    print(f"Status State : {status}")
    print(f"Status Detail: {reason}")
    print(f"Jobs Returned: {len(jobs)}")
    for i, j in enumerate(jobs[:3], 1):
        print(f"  [{i}] Title    : {j.title}")
        print(f"      Company  : {j.company}")
        print(f"      Apply URL: {j.apply_url}")
    return bool(jobs), len(jobs), jobs[:3]

async def run_greenhouse_check():
    print("\n" + "=" * 65)
    print("SOURCE: Greenhouse ATS (boards-api.greenhouse.io)")
    print("=" * 65)
    jobs, status, reason = await search_greenhouse("software", max_results=5)
    print(f"Status State : {status}")
    print(f"Status Detail: {reason}")
    print(f"Jobs Returned: {len(jobs)}")
    for i, j in enumerate(jobs[:3], 1):
        print(f"  [{i}] Title    : {j.title}")
        print(f"      Company  : {j.company}")
        print(f"      Apply URL: {j.apply_url}")
    return bool(jobs), len(jobs), jobs[:3]

async def main():
    print("=" * 65)
    print("JOBPULSE MULTI-SOURCE FEED AUDIT & DIAGNOSTIC VERIFIER")
    print("=" * 65)
    log_config_startup()

    results = {}
    results["Adzuna"] = await run_adzuna_check()
    results["JSearch"] = await run_jsearch_check()
    results["Remotive"] = await run_remotive_check()
    results["Arbeitnow"] = await run_arbeitnow_check()
    results["Greenhouse"] = await run_greenhouse_check()

    print("\n" + "=" * 65)
    print("MULTI-SOURCE AUDIT SUMMARY:")
    for src, (ok, count, top3) in results.items():
        state = f"PASSED ({count} real jobs returned)" if count > 0 else ("CONFIGURED / AUDITED" if ok else "FAILED")
        print(f"  {src:12}: {state}")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(main())

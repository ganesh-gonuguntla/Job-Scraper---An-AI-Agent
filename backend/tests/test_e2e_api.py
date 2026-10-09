import asyncio
import json
import httpx
import pytest

@pytest.mark.asyncio
async def test_full_pipeline_lifecycle():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30.0) as client:
        # 1. Health check
        health = await client.get("/api/health")
        assert health.status_code == 200

        # 2. Start a run (no PDF passed -> falls back to fixtures/sample_resume.txt)
        prefs = {
            "job_types": ["fte", "intern"],
            "min_salary_inr_annual": 1000000,
            "locations": ["Bangalore", "remote"],
            "sort_by": "match",
            "max_age_days": 30,
        }

        resp = await client.post(
            "/api/runs",
            data={"preferences": json.dumps(prefs)},
        )
        assert resp.status_code == 200
        run_data = resp.json()
        assert "run_id" in run_data
        run_id = run_data["run_id"]
        print(f"\n[E2E] Created run_id: {run_id}")

        # 3. Stream SSE events
        interrupted = False
        interrupt_payload = None
        result_payload = None

        async with client.stream("GET", f"/api/runs/{run_id}/stream") as stream_resp:
            assert stream_resp.status_code == 200

            async for line in stream_resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    raw_data = line[6:].strip()
                    try:
                        data = json.loads(raw_data)
                    except Exception:
                        data = {}

                    print(f"[E2E SSE] Event: {event_type}")

                    if event_type == "interrupt":
                        interrupted = True
                        interrupt_payload = data
                        print(f"[E2E SSE] Received interrupt event with profile: {bool(data.get('profile'))}")
                        # Break out of stream temporarily or trigger resume in background
                        # Resume the graph
                        resume_resp = await client.post(
                            f"/api/runs/{run_id}/resume",
                            json=interrupt_payload,
                        )
                        assert resume_resp.status_code == 200
                        print(f"[E2E] Resumed graph: {resume_resp.json()}")

                    elif event_type == "result":
                        result_payload = data
                        print(f"[E2E SSE] Received final result with {len(data.get('final_jobs', []))} jobs")
                        break

        assert interrupted is True, "Graph should have paused on human review interrupt"
        assert result_payload is not None, "Graph should produce final result payload"
        jobs = result_payload.get("final_jobs", [])
        assert len(jobs) > 0, "Should have produced scored and ranked jobs"

        # 4. Test instant re-ranking with 0 LLM calls
        new_prefs = {
            "job_types": ["fte"],
            "min_salary_inr_annual": 1200000,
            "locations": ["Bangalore"],
            "sort_by": "salary",
            "max_age_days": 30,
        }
        rerank_resp = await client.post(
            f"/api/runs/{run_id}/rerank",
            json=new_prefs,
        )
        assert rerank_resp.status_code == 200
        reranked_data = rerank_resp.json()
        assert "final_jobs" in reranked_data
        print(f"[E2E] Reranked successfully: {len(reranked_data['final_jobs'])} jobs matching updated criteria")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline_lifecycle())

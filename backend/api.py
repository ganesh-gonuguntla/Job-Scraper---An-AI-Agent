import asyncio
from contextlib import asynccontextmanager
import json
import logging
import uuid
from typing import Any, Dict, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sse_starlette.sse import EventSourceResponse

from backend.config import DB_PATH
from backend.graph import build_graph
from backend.nodes.ranker import apply_ranker
from backend.schemas import Preferences, Profile, SearchQuery, ScoredJob

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async_graph = None
async_checkpointer = None
saver_cm = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global async_graph, async_checkpointer, saver_cm
    logger.info("Initializing AsyncSqliteSaver checkpointer...")
    saver_cm = AsyncSqliteSaver.from_conn_string(str(DB_PATH))
    async_checkpointer = await saver_cm.__aenter__()
    async_graph = build_graph(checkpointer=async_checkpointer)
    logger.info("LangGraph compiled with AsyncSqliteSaver")
    yield
    if saver_cm:
        await saver_cm.__aexit__(None, None, None)
        logger.info("AsyncSqliteSaver closed")

app = FastAPI(title="Job Scraper & AI Recommender", version="1.0.0", lifespan=lifespan)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory registry for active run queues and resume events
run_queues: Dict[str, asyncio.Queue] = {}
run_resume_events: Dict[str, asyncio.Event] = {}
run_resume_payloads: Dict[str, Any] = {}
active_runs: Dict[str, Dict[str, Any]] = {}

async def run_graph_worker(run_id: str, initial_state: Dict[str, Any]):
    queue = run_queues[run_id]
    thread_config = {"configurable": {"thread_id": run_id}}

    try:
        logger.info(f"Starting graph for run_id: {run_id}")
        current_input = initial_state

        while True:
            interrupted = False
            interrupt_payload = None

            async for chunk in async_graph.astream(
                current_input,
                config=thread_config,
                stream_mode="updates"
            ):
                for node_name, node_update in chunk.items():
                    if node_name == "__interrupt__":
                        continue

                    summary = ""
                    if isinstance(node_update, dict):
                        summary = node_update.get("status_note", "")
                        if not summary:
                            if "candidates" in node_update:
                                summary = f"Found {len(node_update['candidates'])} candidate postings"
                            elif "jobs" in node_update:
                                summary = f"Extracted {len(node_update['jobs'])} job postings"
                            elif "scored_jobs" in node_update:
                                summary = f"Scored {len(node_update['scored_jobs'])} jobs"
                            elif "final_jobs" in node_update:
                                summary = f"Ranked {len(node_update['final_jobs'])} final jobs"

                    await queue.put({
                        "event": "node_end",
                        "data": json.dumps({"node": node_name, "summary": summary or f"Completed {node_name}"})
                    })

            # Check if graph paused on interrupt
            state_snapshot = await async_graph.aget_state(thread_config)

            if state_snapshot.next:
                # Tasks may contain the interrupt payload
                for task in state_snapshot.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        interrupted = True
                        interrupt_payload = task.interrupts[0].value
                        break

            if interrupted and interrupt_payload:
                logger.info(f"Run {run_id} paused at human review interrupt")
                await queue.put({
                    "event": "interrupt",
                    "data": json.dumps(interrupt_payload)
                })

                # Wait until POST /api/runs/{id}/resume provides input
                resume_event = run_resume_events[run_id]
                await resume_event.wait()
                resume_event.clear()

                user_input = run_resume_payloads.get(run_id, {})
                logger.info(f"Resuming run {run_id} with user edits")
                current_input = Command(resume=user_input)
                continue

            # Graph finished normally
            final_jobs_raw = state_snapshot.values.get("final_jobs", [])
            status_note = state_snapshot.values.get("status_note", None)

            # Convert final jobs to JSON-serializable list
            final_jobs_data = []
            for j in final_jobs_raw:
                if hasattr(j, "model_dump"):
                    final_jobs_data.append(j.model_dump())
                elif isinstance(j, dict):
                    final_jobs_data.append(j)

            await queue.put({
                "event": "result",
                "data": json.dumps({
                    "final_jobs": final_jobs_data,
                    "status_note": status_note
                })
            })
            break

    except Exception as e:
        logger.exception(f"Error during graph execution for run {run_id}: {e}")
        await queue.put({
            "event": "error",
            "data": json.dumps({"message": str(e)})
        })
    finally:
        # Send end-of-stream signal
        await queue.put(None)

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "job-matcher"}

@app.post("/api/runs")
async def create_run(
    pdf: Optional[UploadFile] = File(None),
    preferences: str = Form("{}"),
):
    try:
        prefs_data = json.loads(preferences)
        prefs = Preferences.model_validate(prefs_data)
    except Exception:
        prefs = Preferences()

    pdf_bytes = b""
    if pdf:
        pdf_bytes = await pdf.read()

    # Fallback if no PDF uploaded (e.g. mock testing or instant sample)
    if not pdf_bytes:
        from pathlib import Path
        sample_path = Path(__file__).resolve().parent.parent / "fixtures" / "sample_resume.txt"
        if sample_path.exists():
            sample_text = sample_path.read_text(encoding="utf-8")
        else:
            sample_text = "Software Engineer with experience in Python, React, FastAPI, Docker, and PostgreSQL."
        resume_text_initial = sample_text
    else:
        resume_text_initial = ""

    run_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    resume_event = asyncio.Event()

    run_queues[run_id] = queue
    run_resume_events[run_id] = resume_event
    active_runs[run_id] = {
        "preferences": prefs,
        "created_at": str(asyncio.get_event_loop().time()),
    }

    initial_state: Dict[str, Any] = {
        "run_id": run_id,
        "pdf_bytes": pdf_bytes,
        "preferences": prefs,
        "resume_text": resume_text_initial,
        "resume_hash": "",
        "profile": None,
        "queries": [],
        "raw_results": [],
        "seen_urls": set(),
        "candidates": [],
        "batches": [],
        "jobs": [],
        "scored_jobs": [],
        "final_jobs": [],
        "retry_count": 0,
        "gate_passed": False,
        "status_note": None,
        "errors": [],
    }

    # Launch graph worker as background task
    asyncio.create_task(run_graph_worker(run_id, initial_state))

    return {"run_id": run_id}

@app.get("/api/runs/{run_id}/stream")
async def stream_run(run_id: str):
    if run_id not in run_queues:
        raise HTTPException(status_code=404, detail="Run not found")

    queue = run_queues[run_id]

    async def event_generator():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    return EventSourceResponse(event_generator())

@app.post("/api/runs/{run_id}/resume")
async def resume_run(run_id: str, payload: Dict[str, Any]):
    if run_id not in run_resume_events:
        raise HTTPException(status_code=404, detail="Run not found or not waiting for review")

    run_resume_payloads[run_id] = payload
    run_resume_events[run_id].set()
    return {"status": "resumed", "run_id": run_id}

@app.post("/api/runs/{run_id}/rerank")
async def rerank_jobs(run_id: str, preferences: Preferences):
    thread_config = {"configurable": {"thread_id": run_id}}
    state_snapshot = await async_graph.aget_state(thread_config)

    scored_jobs = state_snapshot.values.get("scored_jobs", [])
    if not scored_jobs:
        # Fallback to checking final_jobs
        scored_jobs = state_snapshot.values.get("final_jobs", [])

    reranked = apply_ranker(scored_jobs, preferences)
    reranked_data = [j.model_dump() if hasattr(j, "model_dump") else j for j in reranked]

    return {
        "run_id": run_id,
        "final_jobs": reranked_data,
        "count": len(reranked_data),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)

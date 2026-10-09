from typing import Any, Dict
from backend.config import GOOD_JOBS_MIN, MAX_RETRIES
from backend.state import GraphState

def quality_gate(state: GraphState) -> Dict[str, Any]:
    final_jobs = state.get("final_jobs", [])
    strong_matches = [j for j in final_jobs if j.score >= 50]
    gate_passed = len(strong_matches) >= GOOD_JOBS_MIN

    retry_count = state.get("retry_count", 0)
    note = state.get("status_note")

    if gate_passed:
        note = f"Quality gate passed: found {len(strong_matches)} strong matches"
    elif retry_count >= MAX_RETRIES:
        note = f"Only {len(strong_matches)} strong matches found. Try broader preferences."

    return {
        "gate_passed": gate_passed,
        "status_note": note,
    }

def route_quality_gate(state: GraphState) -> str:
    gate_passed = state.get("gate_passed", False)
    retry_count = state.get("retry_count", 0)

    if gate_passed or retry_count >= MAX_RETRIES:
        return "END"
    return "query_refiner"

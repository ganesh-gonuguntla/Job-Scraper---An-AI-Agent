from typing import Any, Dict
from backend.state import GraphState

def error_end(state: GraphState) -> Dict[str, Any]:
    note = state.get("status_note") or "Could not read resume. Please upload a clear PDF with extractable text."
    errors = state.get("errors", [])
    if not errors:
        errors = [note]
    return {
        "status_note": note,
        "errors": errors,
        "final_jobs": [],
    }

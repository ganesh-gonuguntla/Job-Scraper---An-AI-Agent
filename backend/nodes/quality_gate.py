from typing import Any, Dict
from backend.state import GraphState

def quality_gate(state: GraphState) -> Dict[str, Any]:
    """
    Quality Gate & Expansion Supervisor:
    - Pass condition: At least 15 jobs scoring >= 20.
    - If fewer than 15 reach the results, triggers an expansion loop (max 2 rounds):
      Round 1: drop specific location, add adjacent titles and entry-level/internship variants, add more countries.
      Round 2: broaden to global remote search and cross-functional roles.
    - Communicates expansion actions to the user in the UI.
    """
    final_jobs = state.get("final_jobs", [])
    retry_count = state.get("retry_count", 0)

    # 15 jobs target
    target_met = len(final_jobs) >= 15
    max_rounds_reached = retry_count >= 2

    gate_passed = target_met or max_rounds_reached
    expansion_action = None

    if target_met:
        status_note = f"Quality Gate Passed: Found {len(final_jobs)} high-fit matching job opportunities"
    elif not max_rounds_reached:
        round_num = retry_count + 1
        if round_num == 1:
            expansion_action = "Dropped specific city constraints, added adjacent titles, entry-level/internship variants, and expanded to India, US, and UK boards."
        else:
            expansion_action = "Broadened to worldwide remote queries and expanded seed engineering boards."
        status_note = f"Quality Gate Expansion (Round {round_num}/2): Found {len(final_jobs)} jobs (<15 target). {expansion_action}"
    else:
        status_note = f"Quality Gate Complete: Search concluded with {len(final_jobs)} verified job matches."

    return {
        "gate_passed": gate_passed,
        "status_note": status_note,
        "expansion_action": expansion_action,
    }

def route_quality_gate(state: GraphState) -> str:
    gate_passed = state.get("gate_passed", False)
    retry_count = state.get("retry_count", 0)

    if gate_passed or retry_count >= 2:
        return "END"
    return "query_refiner"

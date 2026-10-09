import re
from typing import Any, Dict, List
from backend.config import JOB_TOKEN_CAP, GROQ_BATCH_TOKEN_BUDGET
from backend.schemas import RawResult
from backend.state import GraphState

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def trim_job_text(text: str, token_cap: int = JOB_TOKEN_CAP) -> str:
    char_cap = token_cap * 4

    # Remove generic filler lines like "About our company", "Perks & Benefits", etc.
    lines = text.splitlines()
    filtered_lines = []
    skip_section = False

    for line in lines:
        line_clean = line.strip().lower()
        if any(h in line_clean for h in ["about the company", "about us", "who we are", "perks & benefits", "why join us"]):
            skip_section = True
            continue
        if any(h in line_clean for h in ["requirements", "responsibilities", "qualifications", "skills", "salary", "compensation", "what you will do"]):
            skip_section = False

        if not skip_section:
            filtered_lines.append(line)

    cleaned_text = "\n".join(filtered_lines) if filtered_lines else text
    # Clean whitespace
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    return cleaned_text[:char_cap].strip()

def build_batches(candidates: List[RawResult]) -> List[List[RawResult]]:
    batches: List[List[RawResult]] = []
    current_batch: List[RawResult] = []
    current_tokens = 0

    for cand in candidates:
        trimmed = trim_job_text(cand.text, JOB_TOKEN_CAP)
        cand.text = trimmed
        item_tokens = estimate_tokens(trimmed) + estimate_tokens(cand.title) + 50

        # Max 5 jobs per batch and under token budget
        if current_batch and (len(current_batch) >= 5 or (current_tokens + item_tokens) > GROQ_BATCH_TOKEN_BUDGET):
            batches.append(current_batch)
            current_batch = [cand]
            current_tokens = item_tokens
        else:
            current_batch.append(cand)
            current_tokens += item_tokens

    if current_batch:
        batches.append(current_batch)

    return batches

def batch_builder(state: GraphState) -> Dict[str, Any]:
    candidates = state.get("candidates", [])
    batches = build_batches(candidates)
    return {
        "batches": batches,
        "status_note": f"Formed {len(batches)} batches for extraction",
    }

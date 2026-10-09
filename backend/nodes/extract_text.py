import io
import re
from typing import Any, Dict
import fitz  # PyMuPDF

from backend.config import RESUME_CHAR_CAP
from backend.cache import cache, get_hash
from backend.state import GraphState

def clean_resume_text(text: str) -> str:
    # Collapse multiple blank lines and spaces
    lines = [line.strip() for line in text.splitlines()]
    # Remove repeated page markers or isolated page numbers
    cleaned_lines = []
    for line in lines:
        if not line:
            continue
        # Drop page numbers like "Page 1 of 2" or isolated digits
        if re.match(r"^(?:page\s*\d+(?:\s*(?:of|\/)\s*\d+)?|\d+)$", line, re.IGNORECASE):
            continue
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    # Collapse excessive whitespace
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Cap at RESUME_CHAR_CAP
    return cleaned[:RESUME_CHAR_CAP].strip()

def ocr_fallback(pdf_bytes: bytes) -> str:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(pdf_bytes)
        text_parts = []
        for img in images:
            text_parts.append(pytesseract.image_to_string(img))
        return "\n".join(text_parts)
    except Exception:
        return ""

def extract_text(state: GraphState) -> Dict[str, Any]:
    pdf_bytes = state.get("pdf_bytes", b"")
    text = state.get("resume_text", "")

    if pdf_bytes:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
        except Exception:
            text = ""

        if len(text.strip()) < 200:
            ocr_text = ocr_fallback(pdf_bytes)
            if len(ocr_text.strip()) > len(text.strip()):
                text = ocr_text

    cleaned = clean_resume_text(text)
    r_hash = get_hash(cleaned)

    # Check cache for existing profile + queries
    cached = cache.get_profile_and_queries(r_hash)
    cached_profile = None
    cached_queries = []
    if cached:
        cached_profile, cached_queries = cached

    updates: Dict[str, Any] = {
        "resume_text": cleaned,
        "resume_hash": r_hash,
    }
    if cached_profile:
        updates["profile"] = cached_profile
        updates["queries"] = cached_queries

    return updates

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Type, TypeVar, Any
from pydantic import BaseModel

from backend.config import (
    GOOGLE_API_KEY,
    GROQ_API_KEY,
    GEMINI_MODEL,
    GROQ_MODEL,
    MOCK_LLM,
    LLM_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_last_call_timestamp = 0.0
_rate_limit_lock = asyncio.Lock()

def _load_canned_fixture(fixture_key: str):
    fixture_path = Path(__file__).resolve().parent.parent / "fixtures" / "canned_responses.json"
    if fixture_path.exists():
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get(fixture_key)
    return None

async def wait_rate_limit():
    global _last_call_timestamp
    async with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_call_timestamp
        if elapsed < LLM_DELAY_SECONDS:
            await asyncio.sleep(LLM_DELAY_SECONDS - elapsed)
        _last_call_timestamp = time.time()

def get_chat_models(temperature: float = 0.0, max_output_tokens: int = 1000):
    """
    Initializes primary and fallback chat models if API keys are present.
    """
    gemini_model = None
    groq_model = None

    if GOOGLE_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini_model = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GOOGLE_API_KEY,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except Exception as e:
            logger.warning(f"Could not initialize Gemini model: {e}")

    if GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            groq_model = ChatGroq(
                model_name=GROQ_MODEL,
                groq_api_key=GROQ_API_KEY,
                temperature=temperature,
                max_tokens=max_output_tokens,
            )
        except Exception as e:
            logger.warning(f"Could not initialize Groq model: {e}")

    return gemini_model, groq_model

def _parse_canned(schema: Type[T], canned: Any) -> T | None:
    if canned is None:
        return None
    if isinstance(canned, list):
        if hasattr(schema, "__annotations__") and "jobs" in schema.__annotations__:
            return schema.model_validate({"jobs": canned})
        if hasattr(schema, "__annotations__") and "scores" in schema.__annotations__:
            return schema.model_validate({"scores": canned})
    return schema.model_validate(canned)

async def invoke_structured(
    schema: Type[T],
    system_prompt: str,
    user_prompt: str,
    preferred_provider: str = "gemini",
    max_tokens: int = 1000,
    fixture_key: str | None = None,
) -> T | None:
    """
    Executes a structured completion with retry/backoff, provider fallbacks,
    and mock mode support.
    """
    await wait_rate_limit()

    if MOCK_LLM or (not GOOGLE_API_KEY and not GROQ_API_KEY):
        logger.info(f"[MOCK_LLM] Returning canned data for fixture key: {fixture_key}")
        if fixture_key:
            canned = _load_canned_fixture(fixture_key)
            if canned:
                return _parse_canned(schema, canned)
        # Fallback empty instance
        try:
            return schema()
        except Exception:
            return None

    gemini_model, groq_model = get_chat_models(temperature=0.0, max_output_tokens=max_tokens)

    # Determine primary and fallback based on preferred_provider
    if preferred_provider == "gemini":
        primary = gemini_model
        fallback = groq_model
    else:
        primary = groq_model
        fallback = gemini_model

    if not primary and not fallback:
        logger.warning("No LLM providers configured, attempting to load fixture")
        if fixture_key:
            canned = _load_canned_fixture(fixture_key)
            if canned:
                return _parse_canned(schema, canned)
        return None

    # Construct messages
    from langchain_core.messages import SystemMessage, HumanMessage
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # Retry loop with exponential backoff and fallback
    providers = []
    if primary:
        providers.append(("primary", primary))
    if fallback and fallback != primary:
        providers.append(("fallback", fallback))

    last_exception = None
    for prov_name, model in providers:
        # Wrap model with structured output
        try:
            structured_model = model.with_structured_output(schema)
        except Exception:
            structured_model = model

        backoff = 2.0
        for attempt in range(3):
            try:
                res = await structured_model.ainvoke(messages)
                if isinstance(res, schema):
                    return res
                elif hasattr(res, "content"):
                    # Parse JSON content manually if needed
                    content_str = res.content
                    if "```json" in content_str:
                        content_str = content_str.split("```json")[1].split("```")[0].strip()
                    elif "```" in content_str:
                        content_str = content_str.split("```")[1].split("```")[0].strip()
                    data = json.loads(content_str)
                    return schema.model_validate(data)
                elif isinstance(res, dict):
                    return schema.model_validate(res)
                return res
            except Exception as e:
                err_str = str(e).lower()
                last_exception = e
                logger.warning(f"Error invoking {prov_name} (attempt {attempt + 1}): {e}")
                if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                else:
                    break  # Non-retryable error on this provider, switch to fallback

    logger.error(f"All LLM attempts failed. Last exception: {last_exception}")
    if fixture_key:
        logger.info(f"Falling back to canned fixture: {fixture_key}")
        canned = _load_canned_fixture(fixture_key)
        if canned:
            return _parse_canned(schema, canned)

    return None

import asyncio
import json
import logging
import time
from typing import Type, TypeVar, Any
from pydantic import BaseModel
import httpx

from backend.config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    GROQ_RESEARCH_MODEL,
    GROQ_EXTRACTION_MODEL,
    GROQ_SCORING_MODEL,
    GROQ_MODEL,
    LLM_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_last_call_timestamp = 0.0
_rate_limit_lock = asyncio.Lock()

async def wait_rate_limit():
    global _last_call_timestamp
    async with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_call_timestamp
        if elapsed < LLM_DELAY_SECONDS:
            await asyncio.sleep(LLM_DELAY_SECONDS - elapsed)
        _last_call_timestamp = time.time()

def get_groq_model_for_role(role: str = "general", temperature: float = 0.0, max_tokens: int = 1500):
    """
    Returns an initialized ChatGroq model instance specialized for the given agent role.
    Roles: 'research' (query generation), 'extraction' (profile extraction), 'scoring' (rubric grader).
    """
    if not GROQ_API_KEY:
        return None

    model_map = {
        "research": GROQ_RESEARCH_MODEL,
        "extraction": GROQ_EXTRACTION_MODEL,
        "scoring": GROQ_SCORING_MODEL,
        "general": GROQ_MODEL,
    }
    target_model = model_map.get(role, GROQ_MODEL)

    try:
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=target_model,
            groq_api_key=GROQ_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logger.warning(f"Could not initialize ChatGroq with model {target_model}: {e}")
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model="openai/gpt-oss-120b",
                groq_api_key=GROQ_API_KEY,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e2:
            logger.error(f"Failed fallback ChatGroq initialization: {e2}")
            return None

async def invoke_groq_structured(
    schema: Type[T],
    system_prompt: str,
    user_prompt: str,
    role: str = "general",
    max_tokens: int = 1500,
) -> T | None:
    if not GROQ_API_KEY:
        return None

    from langchain_core.messages import SystemMessage, HumanMessage
    schema_desc = json.dumps(schema.model_json_schema())
    system_prompt_with_json_directive = (
        f"{system_prompt}\n\nSCHEMA SPECIFICATION:\n{schema_desc}\n\n"
        "IMPORTANT: Respond ONLY in valid JSON matching this schema."
    )
    messages = [
        SystemMessage(content=system_prompt_with_json_directive),
        HumanMessage(content=user_prompt),
    ]

    backoff = 2.0
    for attempt in range(2):
        model = get_groq_model_for_role(role=role, temperature=0.0, max_tokens=max_tokens)
        if not model:
            return None

        try:
            res = await model.ainvoke(messages)
            content_str = res.content if hasattr(res, "content") else str(res)
            if "```json" in content_str:
                content_str = content_str.split("```json")[1].split("```")[0].strip()
            elif "```" in content_str:
                content_str = content_str.split("```")[1].split("```")[0].strip()
            content_str = content_str.strip()
            data = json.loads(content_str)
            if isinstance(data, list):
                if hasattr(schema, "__annotations__") and "scores" in schema.__annotations__:
                    return schema.model_validate({"scores": data})
                if hasattr(schema, "__annotations__") and "queries" in schema.__annotations__:
                    return schema.model_validate({"queries": data})
            return schema.model_validate(data)
        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"Groq [{role}] structured extraction attempt {attempt + 1} failed: {e}")
            if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                await asyncio.sleep(backoff)
                backoff *= 2.0
            else:
                await asyncio.sleep(1.0)
    return None

async def invoke_gemini_structured(
    schema: Type[T],
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
) -> T | None:
    if not GEMINI_API_KEY:
        return None

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
        schema_desc = json.dumps(schema.model_json_schema())
        combined_prompt = (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
            f"SCHEMA SPECIFICATION:\n{schema_desc}\n\n"
            f"INPUT DATA:\n{user_prompt}\n\n"
            f"REQUIRED OUTPUT: Produce a valid JSON object matching the requested schema. Return raw JSON only."
        )
        payload = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "maxOutputTokens": max_tokens,
                "temperature": 0.0,
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        raw_json = parts[0]["text"].strip()
                        if "```json" in raw_json:
                            raw_json = raw_json.split("```json")[1].split("```")[0].strip()
                        elif "```" in raw_json:
                            raw_json = raw_json.split("```")[1].split("```")[0].strip()
                        parsed = json.loads(raw_json)
                        if isinstance(parsed, list):
                            if hasattr(schema, "__annotations__") and "scores" in schema.__annotations__:
                                return schema.model_validate({"scores": parsed})
                            if hasattr(schema, "__annotations__") and "queries" in schema.__annotations__:
                                return schema.model_validate({"queries": parsed})
                        return schema.model_validate(parsed)
            else:
                logger.warning(f"Gemini API returned status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Gemini structured invocation error: {e}")
    return None

async def invoke_structured(
    schema: Type[T],
    system_prompt: str,
    user_prompt: str,
    role: str = "general",
    max_tokens: int = 1500,
    **kwargs,  # absorbs legacy unused kwargs like fixture_key
) -> T | None:
    """
    Executes a structured completion using live LLMs:
    - For 'research' (query synthesis): Uses Gemini first (with Groq fallback)
    - For 'extraction' & 'scoring': Uses Groq first (with Gemini fallback)
    Deterministic temperature=0, rate-limiting, and error logging.
    NEVER falls back to fake/canned/mock data.
    """
    await wait_rate_limit()

    # Groq primary
    if GROQ_API_KEY:
        res = await invoke_groq_structured(schema, system_prompt, user_prompt, role=role, max_tokens=max_tokens)
        if res:
            return res
        logger.info(f"Groq {role} invocation failed, falling back to Gemini.")

    # Gemini fallback
    if GEMINI_API_KEY:
        res = await invoke_gemini_structured(schema, system_prompt, user_prompt, max_tokens=max_tokens)
        if res:
            return res
        logger.info(f"Gemini {role} invocation failed.")

    logger.error(f"All configured LLM providers failed for role '{role}'. No mock data permitted.")
    return None

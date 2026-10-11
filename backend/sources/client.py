import httpx
from typing import Optional

_http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    """
    Returns a shared singleton httpx.AsyncClient with connection pooling.
    Reused across all source adapters to prevent connection starvation.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            follow_redirects=True,
            timeout=25.0,
            headers={
                "User-Agent": "JobPulse/1.0 (Job Aggregation & Career Matching System; Contact: support@jobpulse.ai)"
            }
        )
    return _http_client

async def close_http_client():
    """Closes the shared HTTP client on shutdown."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

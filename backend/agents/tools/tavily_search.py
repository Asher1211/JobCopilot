"""Tavily Search API wrapper with exponential backoff retry."""
import asyncio
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)
TAVILY_URL = "https://api.tavily.com/search"

MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds


async def tavily_search(query: str, max_results: int = 5, api_key: str = "") -> dict:
    """Search Tavily with exponential backoff retry. Uses user key if provided, else server default."""
    key = api_key or settings.tavily_api_key
    if not key:
        return {"results": [], "answer": "", "error": "No Tavily API key configured"}

    last_error: str | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    TAVILY_URL,
                    json={
                        "api_key": key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "advanced",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                if not results and attempt < MAX_RETRIES:
                    logger.warning("Tavily returned empty results, retry %d/%d", attempt + 1, MAX_RETRIES)
                    await asyncio.sleep(BASE_DELAY * (2 ** attempt))
                    continue
                return {
                    "results": results[:max_results],
                    "answer": data.get("answer", ""),
                }

        except Exception as e:
            last_error = str(e)
            logger.warning("Tavily search attempt %d failed: %s", attempt + 1, e)
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BASE_DELAY * (2 ** attempt))

    return {"results": [], "answer": "", "error": f"All {MAX_RETRIES} retries failed: {last_error}"}

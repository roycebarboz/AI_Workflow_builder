"""Web search tool backed by the Tavily search API.

The actual HTTP call is isolated in `_call_tavily` so tests can stub it
out at that boundary (same idea as `LLMClient` for the OpenAI SDK)
without reaching into `httpx` request/response internals.
"""

from __future__ import annotations

import os

import httpx

SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current or external information via Tavily.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                }
            },
            "required": ["query"],
        },
    },
}

_TAVILY_URL = "https://api.tavily.com/search"


def _call_tavily(query: str, api_key: str) -> dict:
    response = httpx.post(
        _TAVILY_URL,
        json={"api_key": api_key, "query": query, "max_results": 5},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def web_search(query: str) -> str:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY is not configured"

    try:
        data = _call_tavily(query, api_key)
    except httpx.HTTPError as exc:
        return f"Error: Tavily search failed ({exc})"

    results = data.get("results", [])
    if not results:
        return f"No results found for '{query}'"

    lines = [
        f"- {r.get('title', 'Untitled')} ({r.get('url', '')}): {r.get('content', '')}"
        for r in results
    ]
    return "\n".join(lines)

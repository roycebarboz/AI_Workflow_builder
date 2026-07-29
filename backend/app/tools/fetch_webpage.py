"""Fetch-webpage tool: retrieves a URL and returns its text content.

The HTTP call is isolated in `_get` so tests can stub it out at that
boundary rather than mocking `httpx` request/response internals.
"""

from __future__ import annotations

import re

import httpx

SCHEMA = {
    "type": "function",
    "function": {
        "name": "fetch_webpage",
        "description": "Fetch a webpage by URL and return its text content.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch, e.g. 'https://example.com'.",
                }
            },
            "required": ["url"],
        },
    },
}

_MAX_CHARS = 2000
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _get(url: str) -> httpx.Response:
    response = httpx.get(url, timeout=10, follow_redirects=True)
    response.raise_for_status()
    return response


def _to_text(html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def fetch_webpage(url: str) -> str:
    try:
        response = _get(url)
    except httpx.HTTPError as exc:
        return f"Error: could not fetch '{url}' ({exc})"

    text = _to_text(response.text)
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "..."
    return text

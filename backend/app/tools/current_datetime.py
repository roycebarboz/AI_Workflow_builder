"""Get-current-datetime tool: returns the current UTC time."""

from __future__ import annotations

from datetime import datetime, timezone

SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_current_datetime",
        "description": "Get the current date and time in UTC, ISO 8601 format.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}


def get_current_datetime() -> str:
    return datetime.now(timezone.utc).isoformat()

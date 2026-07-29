from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .calculator import SCHEMA as CALCULATOR_SCHEMA
from .calculator import calculator
from .current_datetime import SCHEMA as CURRENT_DATETIME_SCHEMA
from .current_datetime import get_current_datetime
from .email_sender import SCHEMA as EMAIL_SCHEMA
from .email_sender import send_email
from .fetch_webpage import SCHEMA as FETCH_WEBPAGE_SCHEMA
from .fetch_webpage import fetch_webpage
from .web_search import SCHEMA as WEB_SEARCH_SCHEMA
from .web_search import web_search


@dataclass(frozen=True)
class ToolSpec:
    schema: dict
    fn: Callable[..., str]


TOOLS: dict[str, ToolSpec] = {
    "calculator": ToolSpec(schema=CALCULATOR_SCHEMA, fn=calculator),
    "web_search": ToolSpec(schema=WEB_SEARCH_SCHEMA, fn=web_search),
    "send_email": ToolSpec(schema=EMAIL_SCHEMA, fn=send_email),
    "fetch_webpage": ToolSpec(schema=FETCH_WEBPAGE_SCHEMA, fn=fetch_webpage),
    "get_current_datetime": ToolSpec(schema=CURRENT_DATETIME_SCHEMA, fn=get_current_datetime),
}


def tool_schemas(enabled: list[str] | None = None) -> list[dict]:
    names = TOOLS.keys() if enabled is None else enabled
    return [TOOLS[name].schema for name in names if name in TOOLS]

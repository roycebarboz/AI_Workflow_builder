from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .calculator import SCHEMA as CALCULATOR_SCHEMA
from .calculator import calculator


@dataclass(frozen=True)
class ToolSpec:
    schema: dict
    fn: Callable[..., str]


# Ticket 01 tracer bullet: single hardcoded tool. More tools land in ticket 08.
TOOLS: dict[str, ToolSpec] = {
    "calculator": ToolSpec(schema=CALCULATOR_SCHEMA, fn=calculator),
}


def tool_schemas(enabled: list[str] | None = None) -> list[dict]:
    names = TOOLS.keys() if enabled is None else enabled
    return [TOOLS[name].schema for name in names if name in TOOLS]

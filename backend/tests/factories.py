"""Shared test data builders."""

from __future__ import annotations


def workflow_graph(system_prompt: str = "", enabled_tools: list[str] | None = None) -> dict:
    """A minimal valid Start -> Agent -> End graph, the fixed topology
    ticket 04 supports (branch/condition nodes land in ticket 05)."""
    return {
        "nodes": [
            {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
            {
                "id": "agent",
                "type": "agent",
                "position": {"x": 200, "y": 0},
                "data": {"system_prompt": system_prompt, "enabled_tools": enabled_tools or []},
            },
            {"id": "end", "type": "end", "position": {"x": 400, "y": 0}, "data": {}},
        ],
        "edges": [
            {"id": "start-agent", "source": "start", "target": "agent"},
            {"id": "agent-end", "source": "agent", "target": "end"},
        ],
    }

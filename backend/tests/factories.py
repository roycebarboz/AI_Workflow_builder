"""Shared test data builders."""

from __future__ import annotations

from typing import Any


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


def branching_workflow_graph(
    keyword: str,
    canned_message: str,
    system_prompt: str = "",
    enabled_tools: list[str] | None = None,
) -> dict:
    """Start -> Condition -> {true: canned End, false: Agent} -> End.

    A condition node gates entry to the agent: messages matching `keyword`
    get a canned response and never reach the LLM; anything else proceeds
    to the agent as normal.
    """
    return {
        "nodes": [
            {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
            {
                "id": "cond",
                "type": "condition",
                "position": {"x": 200, "y": 0},
                "data": {"keyword": keyword},
            },
            {
                "id": "canned-end",
                "type": "end",
                "position": {"x": 400, "y": -80},
                "data": {"message": canned_message},
            },
            {
                "id": "agent",
                "type": "agent",
                "position": {"x": 400, "y": 80},
                "data": {"system_prompt": system_prompt, "enabled_tools": enabled_tools or []},
            },
            {"id": "end", "type": "end", "position": {"x": 600, "y": 80}, "data": {}},
        ],
        "edges": [
            {"id": "start-cond", "source": "start", "target": "cond"},
            {"id": "cond-canned", "source": "cond", "target": "canned-end", "sourceHandle": "true"},
            {"id": "cond-agent", "source": "cond", "target": "agent", "sourceHandle": "false"},
            {"id": "agent-end", "source": "agent", "target": "end"},
        ],
    }


def if_else_workflow_graph(
    branches: list[dict[str, Any]],
    system_prompt: str = "",
    enabled_tools: list[str] | None = None,
) -> dict:
    """Start -> Agent -> If/else -> one End node per branch, plus Else.

    `branches` is a list of `{"id", "label", "keyword"}` dicts, matching the
    if/else node's `data.branches` shape. Each branch (and the implicit
    "else" fallback) routes to its own End node carrying a distinct canned
    message ("Routed: <branch id>"), so tests can tell which branch fired
    from the chat response alone.
    """
    nodes: list[dict] = [
        {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
        {
            "id": "agent",
            "type": "agent",
            "position": {"x": 200, "y": 0},
            "data": {"system_prompt": system_prompt, "enabled_tools": enabled_tools or []},
        },
        {
            "id": "ifelse",
            "type": "if_else",
            "position": {"x": 400, "y": 0},
            "data": {"branches": branches},
        },
    ]
    edges: list[dict] = [
        {"id": "start-agent", "source": "start", "target": "agent"},
        {"id": "agent-ifelse", "source": "agent", "target": "ifelse"},
    ]
    for i, branch in enumerate(branches):
        end_id = f"end_{branch['id']}"
        nodes.append(
            {
                "id": end_id,
                "type": "end",
                "position": {"x": 600, "y": i * 80},
                "data": {"message": f"Routed: {branch['id']}"},
            }
        )
        edges.append(
            {
                "id": f"ifelse-{branch['id']}",
                "source": "ifelse",
                "target": end_id,
                "sourceHandle": branch["id"],
            }
        )
    nodes.append(
        {
            "id": "end_else",
            "type": "end",
            "position": {"x": 600, "y": len(branches) * 80},
            "data": {"message": "Routed: else"},
        }
    )
    edges.append({"id": "ifelse-else", "source": "ifelse", "target": "end_else", "sourceHandle": "else"})
    return {"nodes": nodes, "edges": edges}

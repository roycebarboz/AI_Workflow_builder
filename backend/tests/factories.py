"""Shared test data builders."""

from __future__ import annotations

from typing import Any


def workflow_graph(system_prompt: str = "", enabled_tools: list[str] | None = None) -> dict:
    """A minimal valid Start -> Agent -> End graph."""
    return {
        "nodes": [
            {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
            {
                "id": "agent",
                "type": "agent",
                "position": {"x": 200, "y": 0},
                "data": {
                    "name": "Agent",
                    "system_prompt": system_prompt,
                    "enabled_tools": enabled_tools or [],
                },
            },
            {"id": "end", "type": "end", "position": {"x": 400, "y": 0}, "data": {}},
        ],
        "edges": [
            {"id": "start-agent", "source": "start", "target": "agent"},
            {"id": "agent-end", "source": "agent", "target": "end"},
        ],
    }


def multi_agent_workflow_graph(
    first_system_prompt: str = "",
    second_system_prompt: str = "",
    first_output_format: str | None = None,
    second_output_format: str | None = None,
) -> dict:
    """Start -> Agent1 -> Agent2 -> End — a sequential two-agent chain,
    each with its own name/system prompt/output format."""
    agent1_data: dict[str, Any] = {"name": "Agent 1", "system_prompt": first_system_prompt, "enabled_tools": []}
    if first_output_format:
        agent1_data["output_format"] = first_output_format
    agent2_data: dict[str, Any] = {"name": "Agent 2", "system_prompt": second_system_prompt, "enabled_tools": []}
    if second_output_format:
        agent2_data["output_format"] = second_output_format

    return {
        "nodes": [
            {"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "agent1", "type": "agent", "position": {"x": 200, "y": 0}, "data": agent1_data},
            {"id": "agent2", "type": "agent", "position": {"x": 400, "y": 0}, "data": agent2_data},
            {"id": "end", "type": "end", "position": {"x": 600, "y": 0}, "data": {}},
        ],
        "edges": [
            {"id": "start-agent1", "source": "start", "target": "agent1"},
            {"id": "agent1-agent2", "source": "agent1", "target": "agent2"},
            {"id": "agent2-end", "source": "agent2", "target": "end"},
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
            "data": {
                "name": "Agent",
                "system_prompt": system_prompt,
                "enabled_tools": enabled_tools or [],
            },
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

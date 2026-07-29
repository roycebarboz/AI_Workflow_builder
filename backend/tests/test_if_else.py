"""HTTP-seam tests for if/else node routing on the agent's final answer.

Per the spec's testing decisions: only the LLM client is stubbed; the
if/else node's routing runs for real through the compiled LangGraph
StateGraph, reached via POST /chat like every other chat test.
"""

from __future__ import annotations

import json

from app.llm import ContentDelta, StreamDone
from app.main import app, get_llm_client

from .factories import if_else_workflow_graph

BRANCHES = [
    {"id": "billing", "label": "Billing", "keyword": "billing"},
    {"id": "technical", "label": "Technical", "keyword": "technical"},
]


class FakeLLMClient:
    def __init__(self, turns: list[list]) -> None:
        self._turns = list(turns)

    def stream_chat(self, messages, tools, *, response_format=None):
        return iter(self._turns.pop(0))


def _override_with(turns: list[list]):
    def _get():
        return FakeLLMClient(turns)

    return _get


def _create_workflow(client, branches=BRANCHES) -> str:
    payload = {
        "name": "Triage",
        "graph": if_else_workflow_graph(branches, system_prompt="Answer briefly."),
    }
    response = client.post("/workflows", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_type = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
        events.append((event_type, json.loads(data)))
    return events


def _run_chat(client, workflow_id: str, agent_text: str) -> list[tuple[str, dict]]:
    turns = [[ContentDelta(text=agent_text), StreamDone(finish_reason="stop")]]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        with client.stream(
            "POST",
            "/chat",
            json={"workflow_id": workflow_id, "messages": [{"role": "user", "content": "help"}]},
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    return _parse_sse(body)


def test_routes_to_matching_branch(client):
    workflow_id = _create_workflow(client)
    events = _run_chat(client, workflow_id, "This looks like a billing issue.")
    assert [e[0] for e in events] == ["token", "final_response", "final_response"]
    assert events[0][1] == {"text": "This looks like a billing issue.", "agent_name": "Agent"}
    assert events[-1][1] == {"text": "Routed: billing", "agent_name": None}


def test_falls_through_to_else_when_nothing_matches(client):
    workflow_id = _create_workflow(client)
    events = _run_chat(client, workflow_id, "I have a general question.")
    assert events[-1][1] == {"text": "Routed: else", "agent_name": None}


def test_first_matching_branch_wins(client):
    workflow_id = _create_workflow(client)
    events = _run_chat(client, workflow_id, "This is both a billing and technical issue.")
    assert events[-1][1] == {"text": "Routed: billing", "agent_name": None}


def test_match_is_case_insensitive(client):
    workflow_id = _create_workflow(client)
    events = _run_chat(client, workflow_id, "BILLING problem here.")
    assert events[-1][1] == {"text": "Routed: billing", "agent_name": None}


def test_chained_if_else_nodes(client):
    """A second if/else downstream of the first further narrows the branch
    that didn't match anything in the first node."""
    graph = if_else_workflow_graph([{"id": "billing", "label": "Billing", "keyword": "billing"}])
    graph["nodes"] = [n for n in graph["nodes"] if n["id"] != "end_else"]
    graph["edges"] = [e for e in graph["edges"] if e["id"] != "ifelse-else"]
    graph["nodes"].append(
        {"id": "ifelse2", "type": "if_else", "position": {"x": 800, "y": 0}, "data": {
            "branches": [{"id": "technical", "label": "Technical", "keyword": "technical"}]
        }}
    )
    graph["edges"].append({"id": "ifelse-ifelse2", "source": "ifelse", "target": "ifelse2", "sourceHandle": "else"})
    graph["nodes"].append(
        {"id": "end_technical", "type": "end", "position": {"x": 1000, "y": 0}, "data": {"message": "Routed: technical"}}
    )
    graph["nodes"].append(
        {"id": "end_else2", "type": "end", "position": {"x": 1000, "y": 80}, "data": {"message": "Routed: else2"}}
    )
    graph["edges"].append({"id": "ifelse2-technical", "source": "ifelse2", "target": "end_technical", "sourceHandle": "technical"})
    graph["edges"].append({"id": "ifelse2-else", "source": "ifelse2", "target": "end_else2", "sourceHandle": "else"})

    response = client.post("/workflows", json={"name": "Chained", "graph": graph})
    assert response.status_code == 201
    workflow_id = response.json()["id"]

    events = _run_chat(client, workflow_id, "This is a technical problem.")
    assert events[-1][1] == {"text": "Routed: technical", "agent_name": None}

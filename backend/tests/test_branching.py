"""HTTP-seam tests for condition/branch node routing (ticket 05).

Per the spec's testing decisions: only the LLM client is stubbed; the
condition node's routing runs for real through the compiled LangGraph
StateGraph, reached via POST /chat like every other chat test.
"""

from __future__ import annotations

import json

from app.llm import ContentDelta, StreamDone
from app.main import app, get_llm_client

from .factories import branching_workflow_graph


class FakeLLMClient:
    def __init__(self, turns: list[list]) -> None:
        self._turns = list(turns)

    def stream_chat(self, messages, tools):
        return iter(self._turns.pop(0))


def _override_with(turns: list[list]):
    def _get():
        return FakeLLMClient(turns)

    return _get


def _create_branching_workflow(client) -> str:
    payload = {
        "name": "Support triage",
        "graph": branching_workflow_graph(
            keyword="urgent",
            canned_message="Escalating to a human immediately.",
            system_prompt="You are a support agent.",
        ),
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


def test_condition_true_branch_bypasses_agent_entirely(client):
    workflow_id = _create_branching_workflow(client)
    app.dependency_overrides[get_llm_client] = _override_with([])
    try:
        with client.stream(
            "POST",
            "/chat",
            json={
                "workflow_id": workflow_id,
                "messages": [{"role": "user", "content": "this is urgent, help!"}],
            },
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    events = _parse_sse(body)
    assert [e[0] for e in events] == ["final_response"]
    assert events[0][1] == {"text": "Escalating to a human immediately."}


def test_condition_false_branch_routes_to_agent(client):
    workflow_id = _create_branching_workflow(client)
    turns = [
        [ContentDelta(text="Sure, I can help with that."), StreamDone(finish_reason="stop")],
    ]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        with client.stream(
            "POST",
            "/chat",
            json={
                "workflow_id": workflow_id,
                "messages": [{"role": "user", "content": "what are your hours?"}],
            },
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    events = _parse_sse(body)
    assert [e[0] for e in events] == ["token", "final_response"]
    assert events[-1][1] == {"text": "Sure, I can help with that."}

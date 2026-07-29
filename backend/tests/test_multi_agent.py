"""HTTP-seam tests for multi-agent chains and per-agent output format.

Per the spec's testing decisions: only the LLM client is stubbed; the
agent chain runs for real through the compiled LangGraph StateGraph,
reached via POST /chat like every other chat test.
"""

from __future__ import annotations

import json

from app.llm import ContentDelta, StreamDone
from app.main import app, get_llm_client

from .factories import multi_agent_workflow_graph


class FakeLLMClient:
    """Replays one list of scripted turns per call, recording each call's
    messages/response_format so tests can inspect what each agent sent."""

    def __init__(self, turns: list[list]) -> None:
        self._turns = list(turns)
        self.calls: list[dict] = []

    def stream_chat(self, messages, tools, *, response_format=None):
        self.calls.append({"messages": messages, "response_format": response_format})
        return iter(self._turns.pop(0))


def _install(turns: list[list]) -> FakeLLMClient:
    client = FakeLLMClient(turns)
    app.dependency_overrides[get_llm_client] = lambda: client
    return client


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


def _create_workflow(client, **kwargs) -> str:
    response = client.post(
        "/workflows", json={"name": "Chain", "graph": multi_agent_workflow_graph(**kwargs)}
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_second_agent_sees_first_agents_answer(client):
    workflow_id = _create_workflow(
        client, first_system_prompt="You are agent one.", second_system_prompt="You are agent two."
    )
    turns = [
        [ContentDelta(text="First answer."), StreamDone(finish_reason="stop")],
        [ContentDelta(text="Second answer."), StreamDone(finish_reason="stop")],
    ]
    llm_client = _install(turns)
    try:
        with client.stream(
            "POST",
            "/chat",
            json={"workflow_id": workflow_id, "messages": [{"role": "user", "content": "hi"}]},
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    events = _parse_sse(body)
    assert [e[0] for e in events] == ["token", "final_response", "token", "final_response"]
    assert events[0][1] == {"text": "First answer.", "agent_name": "Agent 1"}
    assert events[1][1] == {"text": "First answer.", "agent_name": "Agent 1"}
    assert events[-1][1] == {"text": "Second answer.", "agent_name": "Agent 2"}

    first_call_messages = llm_client.calls[0]["messages"]
    second_call_messages = llm_client.calls[1]["messages"]
    assert first_call_messages[0] == {"role": "system", "content": "You are agent one."}
    assert second_call_messages[0] == {"role": "system", "content": "You are agent two."}
    # The second agent sees the first agent's answer plus its own system prompt.
    assert {"role": "assistant", "content": "First answer."} in second_call_messages


def test_agent_output_format_json_sets_response_format_and_prompt_hint(client):
    workflow_id = _create_workflow(client, first_output_format="json")
    turns = [
        [ContentDelta(text='{"ok": true}'), StreamDone(finish_reason="stop")],
        [ContentDelta(text="done"), StreamDone(finish_reason="stop")],
    ]
    llm_client = _install(turns)
    try:
        with client.stream(
            "POST",
            "/chat",
            json={"workflow_id": workflow_id, "messages": [{"role": "user", "content": "hi"}]},
        ) as response:
            assert response.status_code == 200
            "".join(response.iter_text())
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    first_call = llm_client.calls[0]
    assert first_call["response_format"] == {"type": "json_object"}
    assert "json" in first_call["messages"][0]["content"].lower()

    second_call = llm_client.calls[1]
    assert second_call["response_format"] is None

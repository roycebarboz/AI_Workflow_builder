"""HTTP-seam tests for POST /chat.

Per the spec's testing decisions: the only external boundary stubbed is
the LLM client (app.llm.LLMClient) — everything else runs for real
through FastAPI's TestClient.
"""

from __future__ import annotations

import json

from app.llm import ContentDelta, StreamDone, ToolCallRequest
from app.main import app, get_llm_client
from app.tools.registry import TOOLS, ToolSpec

from .factories import workflow_graph


class FakeLLMClient:
    """Replays a scripted list of turns, one list of events per call to
    stream_chat, and records each call's messages/tools for inspection."""

    def __init__(self, turns: list[list]) -> None:
        self._turns = list(turns)
        self.calls: list[dict] = []

    def stream_chat(self, messages, tools):
        self.calls.append({"messages": messages, "tools": tools})
        return iter(self._turns.pop(0))


def _override_with(turns: list[list]):
    def _get():
        return FakeLLMClient(turns)

    return _get


def _install_llm_override(turns: list[list]) -> FakeLLMClient:
    """Registers a FakeLLMClient as the get_llm_client override and returns
    it directly, so callers that need to inspect what the agent loop sent
    (messages, tools) don't have to dig it back out of the override closure."""
    client = FakeLLMClient(turns)
    app.dependency_overrides[get_llm_client] = lambda: client
    return client


def _create_workflow(client) -> str:
    payload = {
        "name": "Test workflow",
        "graph": workflow_graph(
            "You are a helpful assistant with access to a calculator tool.", ["calculator"]
        ),
    }
    response = client.post("/workflows", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _create_workflow_full(client) -> dict:
    payload = {
        "name": "Test workflow",
        "graph": workflow_graph(
            "You are a helpful assistant with access to a calculator tool.", ["calculator"]
        ),
    }
    response = client.post("/workflows", json=payload)
    assert response.status_code == 201
    return response.json()


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


def test_chat_direct_answer_no_tool_call(client):
    workflow_id = _create_workflow(client)
    turns = [
        [ContentDelta(text="Hel"), ContentDelta(text="lo!"), StreamDone(finish_reason="stop")],
    ]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
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
    assert [e[0] for e in events] == ["token", "token", "final_response"]
    assert events[-1][1] == {"text": "Hello!"}


def test_chat_with_tool_call(client):
    workflow_id = _create_workflow(client)
    turns = [
        [
            ToolCallRequest(id="call_1", name="calculator", arguments='{"expression": "2 + 2"}'),
            StreamDone(finish_reason="tool_calls"),
        ],
        [ContentDelta(text="4"), StreamDone(finish_reason="stop")],
    ]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        with client.stream(
            "POST",
            "/chat",
            json={
                "workflow_id": workflow_id,
                "messages": [{"role": "user", "content": "what is 2+2"}],
            },
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    events = _parse_sse(body)
    assert [e[0] for e in events] == [
        "tool_call_start",
        "tool_call_result",
        "token",
        "final_response",
    ]
    assert events[0][1] == {"name": "calculator", "arguments": {"expression": "2 + 2"}}
    assert events[1][1] == {"name": "calculator", "result": "4"}
    assert events[-1][1] == {"text": "4"}


def test_chat_surfaces_tool_failure_as_error_event(client, monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(TOOLS, "calculator", ToolSpec(schema=TOOLS["calculator"].schema, fn=_boom))

    workflow_id = _create_workflow(client)
    turns = [
        [
            ToolCallRequest(id="call_1", name="calculator", arguments='{"expression": "2 + 2"}'),
            StreamDone(finish_reason="tool_calls"),
        ],
    ]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        with client.stream(
            "POST",
            "/chat",
            json={
                "workflow_id": workflow_id,
                "messages": [{"role": "user", "content": "what is 2+2"}],
            },
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    events = _parse_sse(body)
    assert [e[0] for e in events] == ["tool_call_start", "error"]
    assert events[1][1] == {"message": "Tool 'calculator' failed: kaboom"}


def test_chat_rejects_empty_messages(client):
    workflow_id = _create_workflow(client)
    response = client.post("/chat", json={"workflow_id": workflow_id, "messages": []})
    assert response.status_code == 422


def test_chat_rejects_unknown_workflow(client):
    turns = [[ContentDelta(text="hi"), StreamDone(finish_reason="stop")]]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        response = client.post(
            "/chat",
            json={
                "workflow_id": "does-not-exist",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
    assert response.status_code == 404


def test_chat_without_pinned_version_uses_current_version(client):
    workflow = _create_workflow_full(client)
    client.put(
        f"/workflows/{workflow['id']}",
        json={
            "name": workflow["name"],
            "graph": workflow_graph("Updated prompt", ["calculator"]),
        },
    )

    turns = [[ContentDelta(text="hi"), StreamDone(finish_reason="stop")]]
    llm_client = _install_llm_override(turns)
    try:
        response = client.post(
            "/chat",
            json={
                "workflow_id": workflow["id"],
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 200
    sent_messages = llm_client.calls[0]["messages"]
    assert sent_messages[0] == {"role": "system", "content": "Updated prompt"}


def test_chat_pinned_to_version_ignores_later_workflow_edits(client):
    workflow = _create_workflow_full(client)
    original_version_id = workflow["current_version_id"]

    client.put(
        f"/workflows/{workflow['id']}",
        json={
            "name": workflow["name"],
            "graph": workflow_graph("Updated prompt", ["calculator"]),
        },
    )

    turns = [[ContentDelta(text="hi"), StreamDone(finish_reason="stop")]]
    llm_client = _install_llm_override(turns)
    try:
        response = client.post(
            "/chat",
            json={
                "workflow_id": workflow["id"],
                "workflow_version_id": original_version_id,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 200
    sent_messages = llm_client.calls[0]["messages"]
    assert sent_messages[0] == {
        "role": "system",
        "content": "You are a helpful assistant with access to a calculator tool.",
    }


def test_chat_rejects_version_from_a_different_workflow(client):
    workflow_a = _create_workflow_full(client)
    workflow_b = _create_workflow_full(client)

    turns = [[ContentDelta(text="hi"), StreamDone(finish_reason="stop")]]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        response = client.post(
            "/chat",
            json={
                "workflow_id": workflow_a["id"],
                "workflow_version_id": workflow_b["current_version_id"],
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 404


def test_chat_rejects_unknown_version_id(client):
    workflow = _create_workflow_full(client)

    turns = [[ContentDelta(text="hi"), StreamDone(finish_reason="stop")]]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        response = client.post(
            "/chat",
            json={
                "workflow_id": workflow["id"],
                "workflow_version_id": "does-not-exist",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    assert response.status_code == 404

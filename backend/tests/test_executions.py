"""HTTP-seam tests for execution history (ticket 07): every /chat run
must persist as an ExecutionRecord, incrementally as it progresses, and
be viewable per-workflow via GET /workflows/{id}/executions[/{id}].
"""

from __future__ import annotations

from app.llm import ContentDelta, StreamDone, ToolCallRequest
from app.main import app, get_llm_client
from app.tools.registry import TOOLS, ToolSpec

from .factories import workflow_graph


class _FakeLLMClient:
    """Replays one list of scripted turns per call to stream_chat. Shared
    across requests within a test via `_override_with` so a test issuing
    multiple /chat calls consumes the queue in order."""

    def __init__(self, turns: list[list]) -> None:
        self._turns = list(turns)

    def stream_chat(self, messages, tools, *, response_format=None):
        return iter(self._turns.pop(0))


def _override_with(turns: list[list]):
    client = _FakeLLMClient(turns)
    return lambda: client


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


def _chat(client, workflow_id, workflow_version_id=None, message="hi"):
    payload = {"workflow_id": workflow_id, "messages": [{"role": "user", "content": message}]}
    if workflow_version_id:
        payload["workflow_version_id"] = workflow_version_id
    with client.stream("POST", "/chat", json=payload) as response:
        assert response.status_code == 200
        for _ in response.iter_text():
            pass


def test_chat_run_appears_in_execution_history_on_completion(client):
    workflow = _create_workflow_full(client)
    turns = [[ContentDelta(text="Hello!"), StreamDone(finish_reason="stop")]]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        _chat(client, workflow["id"])
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    response = client.get(f"/workflows/{workflow['id']}/executions")
    assert response.status_code == 200
    executions = response.json()
    assert len(executions) == 1
    assert executions[0]["workflow_version_id"] == workflow["current_version_id"]
    assert executions[0]["status"] == "completed"
    assert executions[0]["final_response"] == "Hello!"


def test_execution_detail_includes_transcript_and_tool_calls(client):
    workflow = _create_workflow_full(client)
    turns = [
        [
            ToolCallRequest(id="call_1", name="calculator", arguments='{"expression": "2 + 2"}'),
            StreamDone(finish_reason="tool_calls"),
        ],
        [ContentDelta(text="4"), StreamDone(finish_reason="stop")],
    ]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        _chat(client, workflow["id"], message="what is 2+2")
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    execution_id = client.get(f"/workflows/{workflow['id']}/executions").json()[0]["id"]
    detail = client.get(f"/workflows/{workflow['id']}/executions/{execution_id}")
    assert detail.status_code == 200
    body = detail.json()

    assert body["transcript"] == [
        {"role": "user", "content": "what is 2+2"},
        {"role": "assistant", "content": "4"},
    ]
    assert body["tool_calls"] == [
        {"name": "calculator", "arguments": {"expression": "2 + 2"}, "result": "4"}
    ]
    assert body["final_response"] == "4"
    assert body["status"] == "completed"
    assert body["error_message"] is None


def test_execution_record_visible_with_partial_state_when_tool_fails(client, monkeypatch):
    def _boom(**kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(TOOLS, "calculator", ToolSpec(schema=TOOLS["calculator"].schema, fn=_boom))

    workflow = _create_workflow_full(client)
    turns = [
        [
            ToolCallRequest(id="call_1", name="calculator", arguments='{"expression": "2 + 2"}'),
            StreamDone(finish_reason="tool_calls"),
        ],
    ]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        _chat(client, workflow["id"], message="what is 2+2")
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    execution_id = client.get(f"/workflows/{workflow['id']}/executions").json()[0]["id"]
    body = client.get(f"/workflows/{workflow['id']}/executions/{execution_id}").json()

    assert body["status"] == "error"
    assert body["error_message"] == "Tool 'calculator' failed: kaboom"
    # The tool-call-start was recorded even though the run never completed.
    assert body["tool_calls"] == [
        {"name": "calculator", "arguments": {"expression": "2 + 2"}, "result": None}
    ]
    assert body["final_response"] is None


def test_execution_history_keeps_original_version_after_workflow_is_edited(client):
    workflow = _create_workflow_full(client)
    original_version_id = workflow["current_version_id"]

    turns = [[ContentDelta(text="hi"), StreamDone(finish_reason="stop")]]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        _chat(client, workflow["id"], workflow_version_id=original_version_id)
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    client.put(
        f"/workflows/{workflow['id']}",
        json={"name": workflow["name"], "graph": workflow_graph("Updated prompt", ["calculator"])},
    )

    executions = client.get(f"/workflows/{workflow['id']}/executions").json()
    assert len(executions) == 1
    assert executions[0]["workflow_version_id"] == original_version_id


def test_list_executions_orders_most_recent_first(client):
    workflow = _create_workflow_full(client)
    turns = [
        [ContentDelta(text="one"), StreamDone(finish_reason="stop")],
        [ContentDelta(text="two"), StreamDone(finish_reason="stop")],
    ]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        _chat(client, workflow["id"], message="first")
        _chat(client, workflow["id"], message="second")
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    executions = client.get(f"/workflows/{workflow['id']}/executions").json()
    assert [e["final_response"] for e in executions] == ["two", "one"]


def test_list_executions_unknown_workflow_returns_404(client):
    response = client.get("/workflows/does-not-exist/executions")
    assert response.status_code == 404


def test_get_execution_missing_returns_404(client):
    workflow = _create_workflow_full(client)
    response = client.get(f"/workflows/{workflow['id']}/executions/does-not-exist")
    assert response.status_code == 404


def test_get_execution_scoped_to_owning_workflow(client):
    workflow_a = _create_workflow_full(client)
    workflow_b = _create_workflow_full(client)

    turns = [[ContentDelta(text="hi"), StreamDone(finish_reason="stop")]]
    app.dependency_overrides[get_llm_client] = _override_with(turns)
    try:
        _chat(client, workflow_a["id"])
    finally:
        app.dependency_overrides.pop(get_llm_client, None)

    execution_id = client.get(f"/workflows/{workflow_a['id']}/executions").json()[0]["id"]
    response = client.get(f"/workflows/{workflow_b['id']}/executions/{execution_id}")
    assert response.status_code == 404

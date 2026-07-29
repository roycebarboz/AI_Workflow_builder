"""HTTP-seam tests for workflow CRUD, via the real DB session (SQLite
in-memory, see conftest.py) — no mocking below the TestClient boundary.
"""

from __future__ import annotations

from .factories import branching_workflow_graph as _branch_graph
from .factories import if_else_workflow_graph as _if_else_graph
from .factories import workflow_graph as _graph


def test_create_workflow(client):
    response = client.post(
        "/workflows",
        json={
            "name": "Support Bot",
            "graph": _graph("You are a support agent.", ["calculator"]),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Support Bot"
    assert body["system_prompt"] == "You are a support agent."
    assert body["enabled_tools"] == ["calculator"]
    assert body["graph"]["nodes"][1]["data"]["system_prompt"] == "You are a support agent."
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert body["current_version_id"]


def test_create_workflow_rejects_unknown_tool(client):
    response = client.post(
        "/workflows",
        json={"name": "A", "graph": _graph("", ["not-a-real-tool"])},
    )
    assert response.status_code == 422


def test_create_workflow_rejects_blank_name(client):
    response = client.post("/workflows", json={"name": "", "graph": _graph()})
    assert response.status_code == 422


def test_create_workflow_rejects_graph_without_agent_node(client):
    graph = _graph()
    graph["nodes"] = [n for n in graph["nodes"] if n["type"] != "agent"]
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_list_workflows(client):
    client.post("/workflows", json={"name": "A", "graph": _graph()})
    client.post("/workflows", json={"name": "B", "graph": _graph()})

    response = client.get("/workflows")
    assert response.status_code == 200
    names = {w["name"] for w in response.json()}
    assert names == {"A", "B"}


def test_get_workflow(client):
    created = client.post("/workflows", json={"name": "A", "graph": _graph("hi")}).json()

    response = client.get(f"/workflows/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_workflow_missing_returns_404(client):
    response = client.get("/workflows/does-not-exist")
    assert response.status_code == 404


def test_update_workflow(client):
    created = client.post(
        "/workflows", json={"name": "A", "graph": _graph("old prompt")}
    ).json()

    response = client.put(
        f"/workflows/{created['id']}",
        json={
            "name": "A renamed",
            "graph": _graph("new prompt", ["calculator"]),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "A renamed"
    assert body["system_prompt"] == "new prompt"
    assert body["enabled_tools"] == ["calculator"]

    refetched = client.get(f"/workflows/{created['id']}").json()
    assert refetched == body


def test_update_workflow_creates_new_immutable_version(client):
    """Each save creates a new WorkflowVersion and moves current_version_id
    forward — it never overwrites the previous version in place."""
    created = client.post(
        "/workflows", json={"name": "A", "graph": _graph("old prompt")}
    ).json()
    original_version_id = created["current_version_id"]

    updated = client.put(
        f"/workflows/{created['id']}",
        json={"name": "A", "graph": _graph("new prompt")},
    ).json()

    assert updated["current_version_id"] != original_version_id
    assert updated["system_prompt"] == "new prompt"


def test_update_workflow_missing_returns_404(client):
    response = client.put(
        "/workflows/does-not-exist",
        json={"name": "A", "graph": _graph()},
    )
    assert response.status_code == 404


def test_create_workflow_accepts_branching_graph(client):
    response = client.post(
        "/workflows",
        json={
            "name": "Triage",
            "graph": _branch_graph(keyword="urgent", canned_message="Escalating."),
        },
    )
    assert response.status_code == 201
    nodes = response.json()["graph"]["nodes"]
    assert any(n["type"] == "condition" for n in nodes)


def test_create_workflow_rejects_condition_without_keyword(client):
    graph = _branch_graph(keyword="urgent", canned_message="Escalating.")
    for node in graph["nodes"]:
        if node["type"] == "condition":
            node["data"] = {}
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_condition_with_one_branch(client):
    graph = _branch_graph(keyword="urgent", canned_message="Escalating.")
    graph["edges"] = [e for e in graph["edges"] if e["id"] != "cond-canned"]
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_condition_branch_to_end_without_message(client):
    graph = _branch_graph(keyword="urgent", canned_message="Escalating.")
    for node in graph["nodes"]:
        if node["id"] == "canned-end":
            node["data"] = {}
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_agent_edge_to_condition(client):
    graph = _branch_graph(keyword="urgent", canned_message="Escalating.")
    graph["nodes"].append(
        {"id": "cond2", "type": "condition", "position": {"x": 800, "y": 0}, "data": {"keyword": "x"}}
    )
    for edge in graph["edges"]:
        if edge["id"] == "agent-end":
            edge["target"] = "cond2"
    graph["edges"].append({"id": "cond2-a", "source": "cond2", "target": "end", "sourceHandle": "true"})
    graph["edges"].append({"id": "cond2-b", "source": "cond2", "target": "end", "sourceHandle": "false"})
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


_BRANCHES = [{"id": "billing", "label": "Billing", "keyword": "billing"}]


def test_create_workflow_accepts_if_else_graph(client):
    response = client.post(
        "/workflows",
        json={"name": "Triage", "graph": _if_else_graph(_BRANCHES)},
    )
    assert response.status_code == 201
    nodes = response.json()["graph"]["nodes"]
    assert any(n["type"] == "if_else" for n in nodes)


def test_create_workflow_rejects_if_else_without_branches(client):
    graph = _if_else_graph(_BRANCHES)
    for node in graph["nodes"]:
        if node["type"] == "if_else":
            node["data"] = {"branches": []}
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_if_else_branch_missing_keyword(client):
    graph = _if_else_graph([{"id": "billing", "label": "Billing", "keyword": ""}])
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_if_else_duplicate_branch_ids(client):
    graph = _if_else_graph(
        [
            {"id": "billing", "label": "Billing", "keyword": "billing"},
            {"id": "billing", "label": "Billing again", "keyword": "invoice"},
        ]
    )
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_if_else_reserved_else_id(client):
    graph = _if_else_graph([{"id": "else", "label": "Bad", "keyword": "x"}])
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_if_else_missing_else_edge(client):
    graph = _if_else_graph(_BRANCHES)
    graph["edges"] = [e for e in graph["edges"] if e["id"] != "ifelse-else"]
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_start_edge_to_if_else(client):
    graph = _if_else_graph(_BRANCHES)
    for edge in graph["edges"]:
        if edge["id"] == "start-agent":
            edge["target"] = "ifelse"
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_rejects_if_else_branch_to_agent(client):
    graph = _if_else_graph(_BRANCHES)
    for edge in graph["edges"]:
        if edge["id"] == "ifelse-billing":
            edge["target"] = "agent"
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_create_workflow_accepts_sticky_note(client):
    graph = _graph("You are a helpful assistant.")
    graph["nodes"].append(
        {"id": "note1", "type": "sticky_note", "position": {"x": 0, "y": 300}, "data": {"text": "Remember to..."}}
    )
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 201
    nodes = response.json()["graph"]["nodes"]
    assert any(n["type"] == "sticky_note" and n["data"]["text"] == "Remember to..." for n in nodes)


def test_create_workflow_rejects_sticky_note_wired_into_graph(client):
    graph = _graph("You are a helpful assistant.")
    graph["nodes"].append(
        {"id": "note1", "type": "sticky_note", "position": {"x": 0, "y": 300}, "data": {"text": "Note"}}
    )
    graph["edges"].append({"id": "note-agent", "source": "note1", "target": "agent"})
    response = client.post("/workflows", json={"name": "A", "graph": graph})
    assert response.status_code == 422


def test_list_tools(client):
    response = client.get("/tools")
    assert response.status_code == 200
    tools = response.json()
    assert any(t["name"] == "calculator" for t in tools)

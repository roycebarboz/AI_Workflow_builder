"""HTTP-seam tests for workflow CRUD, via the real DB session (SQLite
in-memory, see conftest.py) — no mocking below the TestClient boundary.
"""

from __future__ import annotations

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


def test_update_workflow_missing_returns_404(client):
    response = client.put(
        "/workflows/does-not-exist",
        json={"name": "A", "graph": _graph()},
    )
    assert response.status_code == 404


def test_list_tools(client):
    response = client.get("/tools")
    assert response.status_code == 200
    tools = response.json()
    assert any(t["name"] == "calculator" for t in tools)

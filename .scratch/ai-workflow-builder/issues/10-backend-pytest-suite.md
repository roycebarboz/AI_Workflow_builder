# 10 — Backend pytest suite

**What to build:** A pytest suite covering Workflow/WorkflowVersion CRUD, the agent tool-call loop, and LangGraph branch/routing behavior — all exercised through the single seam of real HTTP requests against the FastAPI `TestClient` and a real test database (disposable Postgres test schema or SQLite in-memory). Only the true external boundary (OpenAI SDK calls, Tavily API calls) is mocked/stubbed at the client boundary.

**Blocked by:** 08 — Remaining tools (branch routing needs 05; tool-coverage tests need all tools from 08 to exist)

**Status:** resolved

- [x] Test suite runs via FastAPI `TestClient` against a real test database — no direct unit-level calls into tool functions or the compiled graph
- [x] Coverage: Workflow/WorkflowVersion CRUD endpoints
- [x] Coverage: chat endpoint's agent-loop behavior (tool call → result → final response), OpenAI client stubbed
- [x] Coverage: LangGraph branch/condition routing takes the expected path for a given input
- [x] Coverage: tool implementations (calculator, mock email sender, web search, extras), with web search's Tavily call stubbed
- [x] Suite runs with a single documented command (e.g. `pytest`) and is referenced in the README

## Comments

Already satisfied by the existing suite — `backend/tests/` (`test_workflows.py`, `test_chat.py`,
`test_if_else.py`, `test_multi_agent.py`, `test_executions.py`, plus one file per tool) runs 68
tests via `TestClient` against a SQLite in-memory DB (`conftest.py`), stubbing only the OpenAI
client and Tavily's HTTP call. README documents `uv run pytest` as the run command. No new work
needed — closing as resolved.

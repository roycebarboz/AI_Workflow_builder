# Mini AI Workflow Builder

Status: ready-for-agent

## Problem Statement

Users who want to build a simple AI-powered workflow — a system prompt paired with tools and some branching logic — currently have to hand-write agent code for every variant. There's no way to visually assemble a workflow (prompt + tools + decision flow), save it, and immediately chat with it. Non-technical iteration (tweak the prompt, toggle a tool, re-run) requires a code change and redeploy instead of a UI action.

## Solution

A local web app with two halves:

1. A **workflow builder** — name a workflow, set its system prompt, enable/disable tools, and (via a drag-and-drop canvas) wire branching/decision logic. Workflows persist and can be edited and re-run later, with immutable version history.
2. A **chat interface** — pick a saved workflow, chat with it, and watch tool calls and intermediate steps stream in live alongside the final response.

Under the hood, each workflow compiles to a LangGraph `StateGraph` (an Agent node that autonomously selects among its enabled tools each turn, plus optional explicit condition/branch nodes for hard-coded routing) running against OpenAI, with every run persisted as execution history tied to the exact workflow version used.

## User Stories

1. As a user, I want to create a new workflow, so that I can start configuring a fresh AI agent.
2. As a user, I want to name a workflow, so that I can find and identify it later.
3. As a user, I want to set a system prompt on a workflow, so that I control the agent's persona and instructions.
4. As a user, I want to see a list of available tools, so that I know what capabilities I can grant the agent.
5. As a user, I want to enable or disable individual tools on a workflow, so that I can scope what the agent is allowed to do.
6. As a user, I want to save a workflow, so that my configuration persists between sessions.
7. As a user, I want to edit a previously saved workflow, so that I can refine it without starting over.
8. As a user, I want to see a list of my saved workflows, so that I can pick one to run or edit.
9. As a user, I want to select a saved workflow and open a chat with it, so that I can interact with the configured agent.
10. As a user, I want to send a message in the chat and see the agent's response stream in token-by-token, so that I get fast feedback instead of waiting for the full response.
11. As a user, I want to see when the agent calls a tool, with the tool's name and arguments, so that I understand what the agent is doing.
12. As a user, I want to see a tool's result once it completes, so that I can verify the agent is reasoning over correct information.
13. As a user, I want to see the final assistant response clearly distinguished from intermediate tool-call steps, so that I can quickly find the answer.
14. As a user, I want to use a calculator tool, so that the agent can perform accurate arithmetic instead of guessing.
15. As a user, I want to use a web search tool, so that the agent can answer questions requiring current/external information.
16. As a user, I want to use a mock email sender tool, so that I can see what the agent would have sent without it actually going out.
17. As a user, I want additional utility tools (e.g. fetch-webpage, get-current-datetime) available, so that workflows can cover more real-world tasks.
18. As a user, I want to visually add condition/branch nodes to a workflow's graph, so that I can hard-code routing logic beyond what the agent decides autonomously.
19. As a user, I want to drag-and-drop wire a workflow's graph on a canvas, so that I can see and edit its structure visually rather than through raw config.
20. As a user, I want the canvas to reflect the same graph schema the backend executes, so that what I see is what actually runs.
21. As a user, I want every save of a workflow to create a new version, so that past executions remain reproducible even after I edit the workflow.
22. As a user, I want a chat run to always use the exact workflow version it was started with, so that editing a workflow mid-conversation doesn't retroactively change past turns.
23. As a user, I want to view execution history for a workflow, so that I can review past runs including their tool calls and outcomes.
24. As a user, I want to bring up the whole app (frontend, backend, database) with one command, so that local setup is fast and reliable.
25. As a user, I want clear README setup instructions and a `.env.example`, so that I know exactly what API keys and steps are required to run the app locally.
26. As a developer extending this app, I want tools to be pluggable, so that I can add a new tool without rewriting the agent loop or graph engine.
27. As a developer extending this app, I want the workflow schema, LangGraph compiler, and canvas editor to share one graph representation, so that visual edits and executable behavior never drift apart.
28. As a user, if the agent hits an error (tool failure, LLM error), I want to see that surfaced in the chat stream, so that I understand the run didn't silently succeed.

## Implementation Decisions

**Scope**: full — all functional requirements plus every listed bonus (streaming, drag-and-drop editor, multiple providers *[dropped, see below]*, workflow versioning, execution history, Docker setup, polished UX).

**Stack**:
- Frontend: React + Vite + TypeScript. React Flow for the drag-and-drop workflow canvas.
- Backend: Python + FastAPI.
- Orchestration: LangGraph (`StateGraph`).
- LLM provider: OpenAI only. The "multiple LLM providers" bonus is explicitly dropped per developer decision — not attempted.
- Persistence: PostgreSQL via SQLAlchemy, migrations via Alembic.
- Repo layout: single monorepo, `frontend/` + `backend/`, one README/.env.example/docker-compose at the root.

**Workflow execution model**: Not a fully manual per-step graph. Each workflow compiles to a LangGraph `StateGraph` containing one Agent node (system prompt + ReAct-style autonomous tool selection over the workflow's enabled tools, looping until it produces a final answer) plus zero or more explicit condition/branch nodes that a user wires on the canvas for hard-coded routing around the Agent node. The canvas's node/edge schema is what the backend compiles directly — no separate translation layer that could drift.

**Tools** (pluggable, enable/disable per workflow):
- Web search — real API via Tavily (key in `.env`).
- Calculator.
- Mock email sender — logs the "sent" email (recipient, subject, body) instead of delivering it.
- 1-2 extra tools for extensibility demonstration (e.g. fetch-webpage, get-current-datetime).

**Streaming**: Server-Sent Events (SSE), one-directional server→client, carrying token deltas, tool-call-start/tool-call-result events, and a final-response event.

**Versioning**: `Workflow` (identity: id, created_at) has many immutable `WorkflowVersion` rows (system prompt, tool config, graph/node config, created_at). `Workflow` tracks a `current_version_id` pointer, updated on each save. A chat run/execution record pins to the specific `WorkflowVersion` id active at run start, not to the mutable `Workflow`, so edits never retroactively alter past runs.

**Execution history**: Each chat run persists as an execution record (workflow_version_id, started_at, message transcript, tool-call log with args/results, final response). Viewable per-workflow.

**Docker**: Single `docker-compose.yml` bringing up frontend, backend, and postgres together; `docker-compose up` is the one-command local setup path. (README also documents non-Docker local setup as a fallback.)

**Build-order constraint (drives ticket sequencing)**: Full scope is in play, but tickets must be ordered so a complete, working, submittable product exists at every step boundary — never a partially-wired later step sitting on top of no working chat. Order, each step blocking the next:

1. **Tracer bullet** — no canvas, no LangGraph, no DB. One hardcoded workflow (system prompt + 1 tool) → FastAPI chat endpoint → real OpenAI tool-call loop → SSE streaming → bare chat UI. Proves the core loop end-to-end.
2. **Persistence** — Postgres + SQLAlchemy + Alembic, Workflow CRUD, workflow config now read from DB instead of hardcoded.
3. **LangGraph swap-in** — replace the manual tool loop with a LangGraph `StateGraph` (Agent node + conditional edges), same observable behavior, now the real orchestration substrate.
4. **Canvas** — React Flow editor to build/save/edit graphs, matching the schema LangGraph already consumes.
5. **Branch/condition nodes** — explicit routing wired on top of the working Agent node.
6. **Remaining bonus** (only after 1-5 are solid, order flexible among these): versioning (`WorkflowVersion` rows), execution history persistence + view, Docker Compose (frontend+backend+postgres), remaining tools, pytest suite.

A ticket in step *n* is unblocked only once every ticket in step *n-1* is resolved. If work stops at any step boundary, everything through that step must independently demo and submit as a complete product.

## Testing Decisions

- Good tests here exercise external/observable behavior (HTTP request in, HTTP/SSE response out, or DB state after a call) — not internal function calls or LangGraph node internals directly.
- **Single seam**: the FastAPI HTTP layer, via `TestClient`. All backend tests (Workflow CRUD, the agent tool-call loop, LangGraph branch/routing behavior) go through real HTTP endpoints against a real test database (disposable Postgres test schema, or SQLite in-memory for speed). Only the true external boundary — the OpenAI SDK calls and the Tavily API call — is mocked/stubbed at the client boundary. No lower-level unit seam (e.g. calling tool functions or the compiled graph directly) is introduced; one seam covers CRUD, orchestration, and branching consistently.
- Modules covered: tool implementations (calculator, mock email sender, web search, extras), Workflow/WorkflowVersion CRUD endpoints, chat endpoint's agent-loop and LangGraph branch routing.
- Frontend and end-to-end browser tests are explicitly out of scope (see below) — no Vitest/RTL/Playwright suite.
- No prior art in-repo (greenfield); pytest + FastAPI `TestClient` is the standard idiom for this stack.

## Out of Scope

- Multiple LLM providers (bonus explicitly dropped — OpenAI only).
- Fully manual, arbitrary per-node execution graphs (no Agent-loop shortcut) — the ReAct-agent-plus-branch-nodes model was chosen instead.
- Authentication / multi-user support — single local user, no login.
- Frontend unit tests, component tests, and end-to-end/browser tests.
- Any LLM provider other than OpenAI, and any local/offline model runner (e.g. Ollama).

## Further Notes

- Package managers: npm for `frontend/`; `uv` or venv+pip for `backend/` (implementation detail, not a hard requirement — pick one and document it in the README).
- No `CONTEXT.md` or ADRs exist yet in this greenfield repo; domain vocabulary above (`Workflow`, `WorkflowVersion`, Agent node, branch/condition node) should seed the domain glossary once `/domain-modeling` is run.
- This spec and its build-order constraint are intended to drive `/to-tickets`: tickets should be generated per numbered step above, with `Blocked by:` edges enforcing that step *n* tickets cannot unblock until all step *n-1* tickets are `resolved`.

# AI Workflow Builder

A local web app for building and chatting with configurable AI workflows (system prompt + tools + decision logic). See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the design write-up, and [`.scratch/ai-workflow-builder/spec.md`](.scratch/ai-workflow-builder/spec.md) for the full spec and build plan.

## What's here

Workflows are built on a drag-and-drop React Flow canvas: drop in agent nodes (each with its own name, system prompt, enabled tools, and text/JSON output format), wire them to if/else branch nodes and end nodes, and annotate with sticky notes. The saved node/edge graph is compiled directly into a LangGraph `StateGraph`, so what you see on the canvas is what executes.

Chat runs stream over SSE, showing token deltas, tool calls with their arguments and results, and the final response, grouped per agent in multi-agent graphs. Every save writes an immutable workflow version, and each run pins to the version it started with, so editing a workflow never changes a conversation already in flight. Runs are persisted and browsable per workflow under Execution history.

Five tools ship: calculator, web search (Tavily), a mock email sender that logs instead of sending, fetch-webpage, and get-current-datetime. Each is enabled per agent node.

## Prerequisites

- Docker and Docker Compose — the one-command path below needs nothing else
- For the manual (non-Docker) path instead: Python 3.13+ and [uv](https://docs.astral.sh/uv/), Node.js 20+ and npm, and a Postgres 16 database reachable at `DATABASE_URL`
- An OpenAI API key either way
- A [Tavily](https://tavily.com/) API key if you want the web search tool to work. Without it that one tool returns an error string; everything else runs fine.

## Setup (Docker — recommended)

1. Copy the env file and fill in your OpenAI API key:

   ```sh
   cp .env.example .env
   ```

   (`.env` needs at least `OPENAI_API_KEY`; the rest have working defaults for Compose.)

2. Bring up the whole stack (frontend, backend, Postgres):

   ```sh
   docker-compose up
   ```

3. Open `http://localhost:5173` and follow [Building your first workflow](#building-your-first-workflow) below.

The backend runs its Alembic migrations automatically on container start. Postgres data persists in a named volume (`postgres-data`) across restarts; `docker-compose down -v` clears it.

## Setup (manual, no Docker)

1. Copy the env file and fill in your OpenAI API key:

   ```sh
   cp .env.example backend/.env
   ```

   (`backend/.env` needs at least `OPENAI_API_KEY`; `OPENAI_MODEL`, `FRONTEND_ORIGIN`, and `DATABASE_URL` have working defaults.)

2. Start Postgres (skip if you already have one running locally matching `DATABASE_URL`):

   ```sh
   docker run -d --name aiwb-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=ai_workflow_builder -p 5432:5432 postgres:16-alpine
   ```

3. Backend:

   ```sh
   cd backend
   uv sync
   uv run alembic upgrade head
   uv run uvicorn app.main:app --reload --port 8000
   ```

4. Frontend (in a second terminal):

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

5. Open the printed Vite URL (default `http://localhost:5173`) and follow the next section.

## Building your first workflow

1. Click **New workflow** and give it a name.
2. Drag an **Agent** node from the left palette onto the canvas. Select it, give it a name (required, and unique within the graph), set a system prompt, then tick the tools it may use. Start with the calculator.
3. Drag an **End** node on, then wire **Start → Agent → End** by dragging between the node handles. Invalid connections are refused as you drag.
4. Flip the top-right toggle to **Run** to chat with the graph without leaving the editor. Run saves first, so you don't have to press **Save** yourself. Ask something requiring arithmetic ("what is 47 * 12?") and the calculator call appears as an intermediate step before the final answer.
5. Back on the dashboard, **Chat** opens the full-page chat for a saved workflow and **History** lists its past runs with their tool calls.

To try branching, drop an **If / else** node between the agent and two end nodes, give one branch a keyword, and wire the branch handles (plus the mandatory `else` handle) to different ends. The agent's final answer is matched against each keyword in order. Setting that agent's output format to JSON makes what it emits predictable enough to branch on reliably.

## Running tests

```sh
cd backend
uv run pytest
```

68 tests, all through the FastAPI `TestClient` against real `/chat`, `/workflows`, and execution-history endpoints, backed by a fresh SQLite in-memory database per test. Only the OpenAI client and the Tavily HTTP call are stubbed. See [`ARCHITECTURE.md`](ARCHITECTURE.md#testing) for why there is only one test seam.

## Project layout

```
backend/            FastAPI app: workflow CRUD, SSE chat endpoint, LangGraph compiler, tools, migrations
frontend/           React + Vite + TypeScript UI: dashboard, React Flow canvas, chat, execution history
docker-compose.yml  One-command local stack (frontend + backend + Postgres)
ARCHITECTURE.md     Architecture and design decisions write-up
.scratch/           Spec and tickets driving this build
```

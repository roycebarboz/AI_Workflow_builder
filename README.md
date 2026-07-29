# AI Workflow Builder

A local web app for building and chatting with configurable AI workflows (system prompt + tools + decision logic). See [`.scratch/ai-workflow-builder/spec.md`](.scratch/ai-workflow-builder/spec.md) for the full spec and build plan.

**Current state — ticket 02 (persistence):** workflows (name, system prompt, tool toggles) are created, listed, edited, and picked from a saved-workflows dashboard, all backed by Postgres via SQLAlchemy/Alembic. The `/chat` endpoint now loads its system prompt and enabled tools from the selected workflow instead of a hardcoded constant. No LangGraph or canvas yet — those land in later tickets (see `.scratch/ai-workflow-builder/issues/`).

## Prerequisites

- Docker and Docker Compose — the one-command path below needs nothing else
- For the manual (non-Docker) path instead: Python 3.13+ and [uv](https://docs.astral.sh/uv/), Node.js 20+ and npm, and a Postgres 16 database reachable at `DATABASE_URL`
- An OpenAI API key either way

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

3. Open `http://localhost:5173`. Create a workflow (name, system prompt, tool toggles), then click "Chat" on its card. Ask something requiring arithmetic (e.g. "what is 47 * 12?") to see the calculator tool call render as an intermediate step before the final response, if the calculator tool is enabled.

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

5. Open the printed Vite URL (default `http://localhost:5173`). Create a workflow (name, system prompt, tool toggles), then click "Chat" on its card. Ask something requiring arithmetic (e.g. "what is 47 * 12?") to see the calculator tool call render as an intermediate step before the final response, if the calculator tool is enabled.

## Running tests

```sh
cd backend
uv run pytest
```

Tests exercise the FastAPI `TestClient` against the real `/chat` and `/workflows` endpoints, backed by a real SQLite in-memory database per test; only the OpenAI client is stubbed (see `backend/tests/test_chat.py`, `backend/tests/test_workflows.py`).

## Project layout

```
backend/            FastAPI app — workflow CRUD, chat endpoint, agent loop, tools, Alembic migrations
frontend/           React + Vite + TypeScript UI — workflows dashboard, workflow form, chat
docker-compose.yml  One-command local stack (frontend + backend + Postgres)
.scratch/           Spec and tickets driving this build
```

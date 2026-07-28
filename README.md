# AI Workflow Builder

A local web app for building and chatting with configurable AI workflows (system prompt + tools + decision logic). See [`.scratch/ai-workflow-builder/spec.md`](.scratch/ai-workflow-builder/spec.md) for the full spec and build plan.

**Current state — ticket 01 (tracer bullet):** one hardcoded workflow (a system prompt + a calculator tool) wired end-to-end: browser chat UI → FastAPI `/chat` endpoint → real OpenAI tool-call loop → Server-Sent Events streamed back to the browser. No database, no LangGraph, no canvas yet — those land in later tickets (see `.scratch/ai-workflow-builder/issues/`).

## Prerequisites

- Python 3.13+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- An OpenAI API key

## Setup

1. Copy the env file and fill in your OpenAI API key:

   ```sh
   cp .env.example backend/.env
   ```

   (`backend/.env` needs at least `OPENAI_API_KEY`; `OPENAI_MODEL` and `FRONTEND_ORIGIN` have working defaults.)

2. Backend:

   ```sh
   cd backend
   uv sync
   uv run uvicorn app.main:app --reload --port 8000
   ```

3. Frontend (in a second terminal):

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

4. Open the printed Vite URL (default `http://localhost:5173`) and chat. Ask something requiring arithmetic (e.g. "what is 47 * 12?") to see the calculator tool call render as an intermediate step before the final response.

## Running tests

```sh
cd backend
uv run pytest
```

Tests exercise the FastAPI `TestClient` against the real `/chat` endpoint; only the OpenAI client is stubbed (see `backend/tests/test_chat.py`).

## Project layout

```
backend/    FastAPI app — chat endpoint, agent loop, tools
frontend/   React + Vite + TypeScript chat UI
.scratch/   Spec and tickets driving this build
```

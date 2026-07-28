# 02 — Workflow persistence (Postgres CRUD)

**What to build:** Workflows move from hardcoded to persisted. A user can create a workflow (name, system prompt, tool toggles), see it in a saved-workflows list, edit it, and pick it to chat with — the chat endpoint from ticket 01 now reads its config from the database instead of a hardcoded constant.

Build the list/detail UI to match `UI_reference/dashboard/workflows-dashboard.html` (and `dashboard.png`) as the visual reference — use a screenshot-verification loop (render the built page, screenshot it, compare against the reference, iterate) rather than eyeballing it once.

**Blocked by:** 01 — Tracer bullet: hardcoded chat loop end-to-end

**Status:** resolved

- [x] Postgres + SQLAlchemy + Alembic migrations set up
- [x] `Workflow` model: id, name, system_prompt, tool config, created_at
- [x] API: create, read, update, list workflows
- [x] Frontend: saved-workflows list page matching `UI_reference/dashboard/` reference (verified via screenshot comparison, not just visual approximation)
- [x] Frontend: create/edit form for name, system prompt, tool enable/disable toggles
- [x] Chat flow: pick a saved workflow from the list, chat endpoint loads its config from DB (no more hardcoded prompt/tool)

## Comments

Implemented: `backend/app/db.py`, `app/models.py`, `app/schemas.py`, `app/workflows_api.py` (Workflow CRUD + `/tools`), Alembic migration `b2f203ca121e`. `/chat` now requires `workflow_id` and 404s on an unknown one. Frontend: `WorkflowsList`, `WorkflowForm`, updated `Chat` + `App` view routing, dark-theme CSS matching `UI_reference/dashboard/workflows-dashboard.html` (screenshot-verified). 15 backend tests pass (SQLite in-memory per test); frontend typecheck/build/lint clean.

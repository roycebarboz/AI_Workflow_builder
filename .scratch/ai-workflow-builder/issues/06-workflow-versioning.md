# 06 — Workflow versioning

**What to build:** Every save of a workflow creates a new immutable `WorkflowVersion` (system prompt, tool config, graph/node config, created_at) instead of overwriting in place. `Workflow` keeps a `current_version_id` pointer that moves forward on each save. Editing a workflow after starting a chat never retroactively changes runs already using an older version.

**Blocked by:** 05 — Branch/condition nodes

**Status:** resolved

- [x] `WorkflowVersion` table: workflow_id, system_prompt, tool config, graph/node config, created_at (immutable once written)
- [x] `Workflow.current_version_id` updated on each save
- [x] Chat run pins to the specific `WorkflowVersion` active at run start
- [x] Editing a workflow mid-conversation does not alter an already-started run's behavior
- [x] Workflow edit UI still reads/writes through the same canvas (ticket 04/05), now against versions

## Comments

`WorkflowVersion` rows are immutable snapshots (graph, system_prompt,
enabled_tools, created_at); `Workflow.current_version_id` is a plain string
column, not a DB-level FK — a real FK would be circular with
`workflow_versions.workflow_id` and versions are never deleted, so nothing
enforces the pointer beyond the app always setting it from a version it just
wrote. `_apply_graph` (workflows_api.py) now creates a new `WorkflowVersion`
and moves `current_version_id` forward on every create/update instead of
overwriting a row in place.

`POST /chat` gained an optional `workflow_version_id`; when present it's
resolved and validated (via `get_workflow_version_or_404`) to belong to the
given `workflow_id`, 404ing otherwise, and the agent loop runs against that
version's graph instead of the live `Workflow.graph`. Omitted, it falls back
to the workflow's current version. The frontend (`Chat.tsx`, `RunPanel.tsx`)
captures `current_version_id` once per chat run — at the point the run
starts, since neither component's chat state survives a remount, and editing
the workflow is unreachable while a run panel is mounted — and resends it on
every turn via `useAgentChat`.

Alembic migration `c3d5e1f7a9b4` backfills every pre-existing workflow with
an initial version and a matching `current_version_id`, using `sa.table`/
`insert()` rather than raw `text()` so the JSON columns get encoded through
the dialect instead of failing on `cannot adapt type 'dict'`. Verified
end-to-end against the real local Postgres container (create → update →
chat pinned to the pre-update version → real OpenAI streaming response;
bogus/cross-workflow `workflow_version_id` both 404); migration upgrade and
downgrade both applied cleanly. Backend: 30 pytest cases pass. Frontend:
typechecks and builds clean.

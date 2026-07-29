# 07 — Execution history

**What to build:** Every chat run persists as an execution record (workflow_version_id, started_at, message transcript, tool-call log with args/results, final response). A user can open a workflow and view its past runs, including what tools were called and what happened.

**Blocked by:** 06 — Workflow versioning (execution records pin to `WorkflowVersion`, which must exist first)

**Status:** resolved

- [x] Execution record model: workflow_version_id, started_at, transcript, tool-call log, final response
- [x] Chat runs write an execution record as they progress (not only on completion, so partial/errored runs are still visible)
- [x] Per-workflow execution history view: list of past runs, each showing transcript + tool calls + final response
- [x] History entries correctly show which `WorkflowVersion` was used, even after the workflow has since been edited

## Comments

`ExecutionRecord` pins to a `WorkflowVersion` id (not the mutable
`Workflow`), matching how chat runs already pin per ticket 06 — editing a
workflow afterward never changes which version a past run's history entry
points at. Records are written incrementally as agent events stream by
(status `running` → `completed`/`error`, `tool_calls` filled in as each
call starts/resolves) rather than only on clean completion, so a run that
errors mid-flight (tool exception, max-rounds, LLM error) still leaves a
visible, partially-populated history entry instead of nothing.

Writing mid-stream needed its own DB session: FastAPI's dependency
exit-stack closes a `Depends(get_db)` session *before* an
`EventSourceResponse` generator's body actually executes, a well-known
gotcha for DB writes inside streaming endpoints. Added
`db.get_session_factory()` so the `/chat` generator opens its own session
scoped to its own lifetime, independent of the request-scoped session
used for the initial workflow/version lookup.

Backend: `GET /workflows/{id}/executions` (list, most-recent-first) and
`GET /workflows/{id}/executions/{id}` (detail incl. transcript/tool
calls/error), both scoped so an execution id from a different workflow
404s. Frontend: a master-detail history view reachable from a "History"
button on each workflow card, reusing the chat page's message/step
styling. 38 backend pytest cases pass (8 new); frontend typechecks and
builds clean.

One caveat noted during review, not fixed here: since `/chat` is
stateless and the frontend resends full history each turn, one
`ExecutionRecord` = one turn, so a multi-turn conversation shows as
several history entries with growing transcripts rather than one grouped
"run." This follows from ticket 03's stateless `/chat` design and matches
the ticket's field list (one `final_response` per record); grouping by
conversation would be a larger, separate change.

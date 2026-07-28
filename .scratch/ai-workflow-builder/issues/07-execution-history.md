# 07 — Execution history

**What to build:** Every chat run persists as an execution record (workflow_version_id, started_at, message transcript, tool-call log with args/results, final response). A user can open a workflow and view its past runs, including what tools were called and what happened.

**Blocked by:** 06 — Workflow versioning (execution records pin to `WorkflowVersion`, which must exist first)

**Status:** ready-for-agent

- [ ] Execution record model: workflow_version_id, started_at, transcript, tool-call log, final response
- [ ] Chat runs write an execution record as they progress (not only on completion, so partial/errored runs are still visible)
- [ ] Per-workflow execution history view: list of past runs, each showing transcript + tool calls + final response
- [ ] History entries correctly show which `WorkflowVersion` was used, even after the workflow has since been edited

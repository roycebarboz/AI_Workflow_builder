# 06 — Workflow versioning

**What to build:** Every save of a workflow creates a new immutable `WorkflowVersion` (system prompt, tool config, graph/node config, created_at) instead of overwriting in place. `Workflow` keeps a `current_version_id` pointer that moves forward on each save. Editing a workflow after starting a chat never retroactively changes runs already using an older version.

**Blocked by:** 05 — Branch/condition nodes

**Status:** ready-for-agent

- [ ] `WorkflowVersion` table: workflow_id, system_prompt, tool config, graph/node config, created_at (immutable once written)
- [ ] `Workflow.current_version_id` updated on each save
- [ ] Chat run pins to the specific `WorkflowVersion` active at run start
- [ ] Editing a workflow mid-conversation does not alter an already-started run's behavior
- [ ] Workflow edit UI still reads/writes through the same canvas (ticket 04/05), now against versions

# 05 — Branch/condition nodes

**What to build:** A user can add explicit condition/branch nodes on the canvas to hard-code routing around the autonomous Agent node (beyond what the agent decides on its own). The LangGraph compiler honors these nodes when executing a chat run.

**Blocked by:** 04 — Drag-and-drop canvas (React Flow)

**Status:** ready-for-agent

- [ ] Canvas supports adding/wiring condition/branch node types alongside the Agent node
- [ ] Saved graph (including branch nodes) round-trips through the same schema the backend compiles
- [ ] LangGraph compiler translates branch/condition nodes into real conditional edges in the `StateGraph`
- [ ] A workflow with a branch node demonstrably routes differently depending on the condition, verified via a chat run

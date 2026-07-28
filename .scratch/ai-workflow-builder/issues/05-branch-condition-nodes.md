# 05 — Branch/condition nodes

**What to build:** A user can add explicit condition/branch nodes on the canvas to hard-code routing around the autonomous Agent node (beyond what the agent decides on its own). The LangGraph compiler honors these nodes when executing a chat run.

**Blocked by:** 04 — Drag-and-drop canvas (React Flow)

**Status:** resolved

- [x] Canvas supports adding/wiring condition/branch node types alongside the Agent node
- [x] Saved graph (including branch nodes) round-trips through the same schema the backend compiles
- [x] LangGraph compiler translates branch/condition nodes into real conditional edges in the `StateGraph`
- [x] A workflow with a branch node demonstrably routes differently depending on the condition, verified via a chat run

## Comments

Condition nodes gate entry to the Agent node (pre-agent routing): a keyword
match against the latest user message routes either to a canned response
(bypassing the LLM entirely) or through to the agent as normal. The Agent
node's own outgoing edge must lead directly to an End node — conditions
don't sit downstream of the agent, since the agent always emits its own
final response once it stops calling tools, and a downstream
condition/end could otherwise emit a contradictory second one. Any End
node reached directly from a condition branch requires a non-empty canned
`message`; manual testing showed a condition pointing at a plain End
silently produced an empty chat response otherwise.

Verified via Playwright browser automation (drag-drop, wiring, edge
deletion/rewiring, save round-trip) and real `POST /chat` calls showing
the keyword-matching branch skip the LLM while the other branch reaches
the real agent. Backend: 25 pytest cases pass. Frontend: typechecks and
builds clean.

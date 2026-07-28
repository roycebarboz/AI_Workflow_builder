# 03 — LangGraph swap-in

**What to build:** Replace the manual OpenAI tool-call loop from ticket 01 with a LangGraph `StateGraph` (one Agent node running the system prompt + ReAct-style autonomous tool selection over the workflow's enabled tools). Observable behavior from the user's side — chat, tool-call steps, streaming, final response — stays identical; the orchestration substrate underneath is now the real one every later ticket (branching, versioning) builds on.

**Blocked by:** 02 — Workflow persistence (Postgres CRUD)

**Status:** resolved

- [x] Chat endpoint compiles and runs a LangGraph `StateGraph` instead of the hand-rolled loop
- [x] Agent node reads system prompt + enabled tools from the workflow's DB config
- [x] SSE streaming behavior (token deltas, tool-call-start/result, final response) unchanged from the user's perspective
- [x] Existing chat flow (pick workflow → chat → see steps → final response) still works end-to-end

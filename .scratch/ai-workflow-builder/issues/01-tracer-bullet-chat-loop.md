# 01 — Tracer bullet: hardcoded chat loop end-to-end

**What to build:** One hardcoded workflow (a fixed system prompt + one tool, e.g. calculator) reachable through a bare chat UI. User types a message, the message hits a FastAPI chat endpoint, the backend runs a real OpenAI tool-call loop (model may call the calculator tool, gets the result, replies), and the response streams back to the browser over SSE token-by-token. No database, no LangGraph, no canvas yet — this proves the core request→LLM→tool→stream→response path works end-to-end.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] FastAPI backend with a `/chat` (or similar) SSE endpoint
- [x] Hardcoded system prompt + one tool (e.g. calculator) wired into a real OpenAI tool-call loop
- [x] SSE stream carries token deltas, tool-call-start/result events, and a final-response event
- [x] Minimal frontend chat UI: send a message, see tool-call steps and the streamed final response render distinctly
- [x] README documents how to run this slice locally (env vars, start commands)

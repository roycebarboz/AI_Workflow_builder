# 08 — Remaining tools (web search, mock email sender, extras)

**What to build:** Beyond the single tool from ticket 01, add the rest of the tool set: real web search (Tavily), a mock email sender (logs recipient/subject/body instead of sending), and 1-2 extra utility tools (e.g. fetch-webpage, get-current-datetime). All are pluggable and can be enabled/disabled per workflow from the existing tool-toggle UI, satisfying the ≥3-tool functional requirement.

**Blocked by:** 05 — Branch/condition nodes (agent loop and tool-toggle UI must already be solid)

**Status:** resolved

- [x] Web search tool backed by Tavily API (key read from `.env`)
- [x] Mock email sender tool: logs recipient, subject, body instead of delivering
- [x] 1-2 extra tools (e.g. fetch-webpage, get-current-datetime)
- [x] Each new tool follows the existing pluggable tool interface — no changes needed to the agent loop or graph engine to add it
- [x] All new tools appear in the tool-toggle UI and can be enabled/disabled per workflow
- [x] `.env.example` updated with any new required keys (e.g. Tavily)

## Comments

Four new tools land in `backend/app/tools/`: `web_search` (Tavily,
`_call_tavily` isolated as the HTTP boundary so tests stub it rather than
mocking `httpx` directly), `send_email` (mock, logs recipient/subject/body
and returns a confirmation string), `fetch_webpage` (strips
`<script>`/`<style>` contents and tags, truncates to 2000 chars), and
`get_current_datetime` (UTC ISO 8601, no args). Each is a `SCHEMA` dict +
plain function, registered in `backend/app/tools/registry.py`'s `TOOLS`
dict — exactly the ticket-01 pattern, no changes to `agent.py`'s
`_tools_node`/`_build_graph`/`run_agent_loop`.

The `/tools` endpoint and the frontend's tool-toggle UI are both already
data-driven off the `TOOLS` registry (from tickets 01/04), so all four
tools show up and are toggleable per-workflow with zero frontend changes.

`httpx` was promoted from a transitive to an explicit backend dependency
since `web_search`/`fetch_webpage` call it directly. Tests: unit tests per
tool (mirroring `test_calculator.py`, monkeypatching each tool's HTTP-call
seam) plus one `/chat`-level integration test
(`test_chat_with_send_email_tool`) proving end-to-end registry wiring
through the real agent tool-call loop. 50 backend pytest cases pass (13
new); frontend typechecks clean (no frontend files changed).

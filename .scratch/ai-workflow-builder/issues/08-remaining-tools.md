# 08 — Remaining tools (web search, mock email sender, extras)

**What to build:** Beyond the single tool from ticket 01, add the rest of the tool set: real web search (Tavily), a mock email sender (logs recipient/subject/body instead of sending), and 1-2 extra utility tools (e.g. fetch-webpage, get-current-datetime). All are pluggable and can be enabled/disabled per workflow from the existing tool-toggle UI, satisfying the ≥3-tool functional requirement.

**Blocked by:** 05 — Branch/condition nodes (agent loop and tool-toggle UI must already be solid)

**Status:** ready-for-agent

- [ ] Web search tool backed by Tavily API (key read from `.env`)
- [ ] Mock email sender tool: logs recipient, subject, body instead of delivering
- [ ] 1-2 extra tools (e.g. fetch-webpage, get-current-datetime)
- [ ] Each new tool follows the existing pluggable tool interface — no changes needed to the agent loop or graph engine to add it
- [ ] All new tools appear in the tool-toggle UI and can be enabled/disabled per workflow
- [ ] `.env.example` updated with any new required keys (e.g. Tavily)

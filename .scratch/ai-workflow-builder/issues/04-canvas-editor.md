# 04 — Drag-and-drop canvas (React Flow)

**What to build:** Replace the plain create/edit form from ticket 02 with a visual drag-and-drop canvas: name the workflow, set its system prompt, toggle tools, and see/wire the workflow's graph (currently just the single Agent node) on a canvas. The canvas's node/edge schema is exactly what the backend's LangGraph compiler consumes — no separate translation layer that could drift.

Build the UI to match `UI_reference/editior/workflow-builder.html` and both `workflow_editor_edit_mode.png` / `workflow_editor_preview_mode.png` (edit mode and preview mode) as the visual reference — use a screenshot-verification loop (render the built page, screenshot it, compare against the reference, iterate) rather than a one-shot visual approximation.

**Blocked by:** 03 — LangGraph swap-in

**Status:** ready-for-agent

- [ ] React Flow canvas embedded in the workflow editor page
- [ ] Canvas shows the workflow's graph (system prompt on Agent node, tool toggles) and edit mode matches `UI_reference/editior/workflow_editor_edit_mode.png`
- [ ] A preview/read-only mode matches `UI_reference/editior/workflow_editor_preview_mode.png`
- [ ] Saving from the canvas persists the same schema the backend LangGraph compiler already reads (ticket 03) — verified by chatting with a workflow edited purely via canvas
- [ ] Screenshot-verification loop used during build: rendered canvas compared against the reference HTML/screenshots, not just implemented from memory

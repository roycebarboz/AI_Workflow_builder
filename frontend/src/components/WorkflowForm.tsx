import { useEffect, useState, type FormEvent } from "react";
import { createWorkflow, listTools, updateWorkflow } from "../api/workflows";
import type { ToolInfo, Workflow } from "../types";

interface WorkflowFormProps {
  workflow: Workflow | null;
  onSaved: (workflow: Workflow) => void;
  onCancel: () => void;
}

export function WorkflowForm({ workflow, onSaved, onCancel }: WorkflowFormProps) {
  const [name, setName] = useState(workflow?.name ?? "");
  const [systemPrompt, setSystemPrompt] = useState(workflow?.system_prompt ?? "");
  const [enabledTools, setEnabledTools] = useState<Set<string>>(
    new Set(workflow?.enabled_tools ?? [])
  );
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTools()
      .then(setTools)
      .catch((err) => setError((err as Error).message));
  }, []);

  function toggleTool(toolName: string) {
    setEnabledTools((prev) => {
      const next = new Set(prev);
      if (next.has(toolName)) next.delete(toolName);
      else next.add(toolName);
      return next;
    });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || isSaving) return;

    setIsSaving(true);
    setError(null);
    const input = {
      name: name.trim(),
      system_prompt: systemPrompt,
      enabled_tools: Array.from(enabledTools),
    };

    try {
      const saved = workflow
        ? await updateWorkflow(workflow.id, input)
        : await createWorkflow(input);
      onSaved(saved);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="5" cy="6" r="2.2" />
              <circle cx="19" cy="6" r="2.2" />
              <circle cx="12" cy="18" r="2.2" />
              <path d="M5 8.2V12a2 2 0 002 2h1" />
              <path d="M19 8.2V12a2 2 0 01-2 2h-1" />
            </svg>
          </span>
          Workflow Builder
        </div>
      </div>

      <main className="main main-narrow">
        <div className="page-head">
          <div>
            <h1>{workflow ? "Edit workflow" : "New workflow"}</h1>
            <p>Configure the system prompt and tools this agent can use.</p>
          </div>
        </div>

        <form className="form-panel" onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">Name</span>
            <input
              className="field-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Support Ticket Assistant"
              required
            />
          </label>

          <label className="field">
            <span className="field-label">System prompt</span>
            <textarea
              className="field-input field-textarea"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are a helpful assistant that..."
              rows={6}
            />
          </label>

          <div className="field">
            <span className="field-label">Tools</span>
            <div className="tool-toggle-list">
              {tools.map((tool) => (
                <label className="tool-toggle" key={tool.name}>
                  <input
                    type="checkbox"
                    checked={enabledTools.has(tool.name)}
                    onChange={() => toggleTool(tool.name)}
                  />
                  <div>
                    <div className="tool-toggle-name">{tool.name}</div>
                    <div className="tool-toggle-desc">{tool.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="error-text">{error}</p>}

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={!name.trim() || isSaving}>
              {isSaving ? "Saving…" : "Save workflow"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

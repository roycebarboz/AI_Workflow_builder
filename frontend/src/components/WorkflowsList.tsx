import { useEffect, useState } from "react";
import { deleteWorkflow, listWorkflows } from "../api/workflows";
import { relativeTime } from "../lib/relativeTime";
import type { Workflow } from "../types";
import { ConfirmDialog } from "./ConfirmDialog";

interface WorkflowsListProps {
  onNew: () => void;
  onEdit: (workflow: Workflow) => void;
  onChat: (workflow: Workflow) => void;
  onHistory: (workflow: Workflow) => void;
  refreshKey: number;
}

export function WorkflowsList({ onNew, onEdit, onChat, onHistory, refreshKey }: WorkflowsListProps) {
  const [workflows, setWorkflows] = useState<Workflow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Workflow | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listWorkflows()
      .then((data) => {
        if (!cancelled) setWorkflows(data);
      })
      .catch((err) => {
        if (!cancelled) setError((err as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  async function confirmDelete() {
    if (!pendingDelete) return;
    setIsDeleting(true);
    try {
      await deleteWorkflow(pendingDelete.id);
      setWorkflows((prev) => prev?.filter((w) => w.id !== pendingDelete.id) ?? prev);
      setPendingDelete(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsDeleting(false);
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
          AI Workflow Builder
        </div>
      </div>

      <main className="main">
        <div className="page-head">
          <div>
            <h1>Workflows</h1>
            <p>Every agent workflow you've built, in one place.</p>
          </div>
          <button className="btn-primary" onClick={onNew}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New workflow
          </button>
        </div>

        {error && <p className="error-text">Couldn't load workflows: {error}</p>}

        {workflows && workflows.length === 0 && (
          <p className="empty-state">No workflows yet — create one to get started.</p>
        )}

        <div className="grid">
          {workflows?.map((workflow) => (
            <article className="card" key={workflow.id} onClick={() => onEdit(workflow)}>
              <span className="card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="5" cy="6" r="2.2" />
                  <circle cx="19" cy="6" r="2.2" />
                  <circle cx="12" cy="18" r="2.2" />
                  <path d="M5 8.2V12a2 2 0 002 2h1" />
                  <path d="M19 8.2V12a2 2 0 01-2 2h-1" />
                </svg>
              </span>
              <h3 className="card-title">{workflow.name}</h3>
              <p className="card-desc">
                {workflow.system_prompt || "No system prompt set yet."}
              </p>
              <div className="node-chips">
                {workflow.enabled_tools.length === 0 ? (
                  <span className="node-chip c-cond">No tools enabled</span>
                ) : (
                  workflow.enabled_tools.map((tool) => (
                    <span className="node-chip c-agent" key={tool}>
                      {tool}
                    </span>
                  ))
                )}
              </div>
              <div className="card-foot">
                <span className="edited">Edited {relativeTime(workflow.updated_at)}</span>
                <div className="card-foot-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      onHistory(workflow);
                    }}
                  >
                    History
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      onChat(workflow);
                    }}
                  >
                    Chat
                  </button>
                  <button
                    type="button"
                    className="btn-danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPendingDelete(workflow);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </main>

      {pendingDelete && (
        <ConfirmDialog
          title={`Delete "${pendingDelete.name}"?`}
          desc="This permanently deletes the workflow, its saved versions, and its chat history. This can't be undone."
          confirmLabel="Delete"
          isBusy={isDeleting}
          onConfirm={() => void confirmDelete()}
          onCancel={() => setPendingDelete(null)}
        />
      )}
    </div>
  );
}

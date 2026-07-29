import { useEffect, useState } from "react";
import { getExecution, listExecutions } from "../api/executions";
import { relativeTime } from "../lib/relativeTime";
import type { ExecutionDetail, ExecutionSummary } from "../types";

interface ExecutionHistoryProps {
  workflowId: string;
  workflowName: string;
  onBack: () => void;
}

function statusLabel(status: ExecutionSummary["status"]): string {
  if (status === "completed") return "Completed";
  if (status === "error") return "Error";
  return "Running";
}

export function ExecutionHistory({ workflowId, workflowName, onBack }: ExecutionHistoryProps) {
  const [executions, setExecutions] = useState<ExecutionSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ExecutionDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listExecutions(workflowId)
      .then((data) => {
        if (cancelled) return;
        setExecutions(data);
        if (data.length > 0) setSelectedId(data[0].id);
      })
      .catch((err) => {
        if (!cancelled) setError((err as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, [workflowId]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    setDetail(null);
    setDetailError(null);
    getExecution(workflowId, selectedId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) setDetailError((err as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, [workflowId, selectedId]);

  return (
    <div className="app">
      <div className="topbar">
        <button type="button" className="btn-link" onClick={onBack}>
          ← Workflows
        </button>
      </div>

      <main className="main">
        <div className="page-head">
          <div>
            <h1>Execution history</h1>
            <p>{workflowName}</p>
          </div>
        </div>

        {error && <p className="error-text">Couldn't load execution history: {error}</p>}

        {executions && executions.length === 0 && (
          <p className="empty-state">No runs yet — chat with this workflow to see history here.</p>
        )}

        {executions && executions.length > 0 && (
          <div className="history-layout">
            <div className="history-list">
              {executions.map((execution) => (
                <button
                  type="button"
                  key={execution.id}
                  className={
                    "history-item" + (execution.id === selectedId ? " active" : "")
                  }
                  onClick={() => setSelectedId(execution.id)}
                >
                  <span className={`status-badge status-${execution.status}`}>
                    {statusLabel(execution.status)}
                  </span>
                  <span className="history-item-time">{relativeTime(execution.started_at)}</span>
                  <span className="history-item-preview">
                    {execution.final_response || "(no response yet)"}
                  </span>
                </button>
              ))}
            </div>

            <div className="history-detail">
              {detailError && <p className="error-text">Couldn't load run: {detailError}</p>}

              {detail && (
                <>
                  <div className="history-detail-head">
                    <span className={`status-badge status-${detail.status}`}>
                      {statusLabel(detail.status)}
                    </span>
                    <span className="history-item-time">
                      Started {relativeTime(detail.started_at)}
                    </span>
                  </div>

                  {/* One ExecutionRecord = one /chat call: `transcript` is the
                      full conversation resent as context, but `tool_calls`
                      and the error (if any) belong only to this run's final
                      turn — so they render after the transcript, not
                      nested per-message the way Chat.tsx nests steps
                      inside a single live turn. */}
                  <div className="chat-history">
                    {detail.transcript.map((message, i) => (
                      <div className={`message ${message.role}`} key={i}>
                        {message.content}
                      </div>
                    ))}

                    {detail.tool_calls.map((call, i) => (
                      <div className="step tool-call" key={i}>
                        <div className="step-label">
                          🔧 {call.name}({JSON.stringify(call.arguments)})
                        </div>
                        {call.result !== null && <div className="step-result">→ {call.result}</div>}
                      </div>
                    ))}

                    {detail.status === "error" && detail.error_message && (
                      <div className="step error">⚠️ {detail.error_message}</div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

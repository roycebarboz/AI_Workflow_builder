import { Fragment, type ReactNode } from "react";
import { useAgentChat } from "../../hooks/useAgentChat";
import { AgentIcon, ChevronIcon, EditIcon, EndIcon, SendIcon, StartIcon } from "./icons";

interface RunPanelProps {
  workflowId: string;
  workflowVersionId: string;
}

function TraceRow({
  icon,
  kind,
  name,
  type,
  defaultOpen,
  children,
}: {
  icon: ReactNode;
  kind: "start" | "agent" | "end";
  name: string;
  type: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details className="trace-row" open={defaultOpen}>
      <summary>
        <span className="chev">
          <ChevronIcon />
        </span>
        <span className={`trace-ico tr-${kind}`}>{icon}</span>
        <span className="trace-name">{name}</span>
        <span className="trace-type">{type}</span>
      </summary>
      <div className="trace-body">{children}</div>
    </details>
  );
}

export function RunPanel({ workflowId, workflowVersionId }: RunPanelProps) {
  const { turns, input, setInput, sendMessage, isSending, reset } = useAgentChat(
    workflowId,
    workflowVersionId
  );

  return (
    <div className="run-panel">
      <div className="run-head">
        <span className="run-head-title">Preview</span>
        <button type="button" className="new-chat-btn" onClick={reset}>
          <EditIcon />
          New chat
        </button>
      </div>

      <div className="run-body">
        {turns.length === 0 ? (
          <div className="run-empty">
            <span className="icon">
              <EditIcon />
            </span>
            <b>Preview your agent</b>
            <span>Prompt the agent as if you're the user. It'll run through the workflow node by node.</span>
          </div>
        ) : (
          <div className="run-body-scroll">
            {turns.map((turn, i) => {
              const hasError = turn.steps.some((s) => s.kind === "error");
              return (
                <Fragment key={i}>
                  <div className="msg-user">{turn.user.content}</div>

                  <div className="trace">
                    <TraceRow icon={<StartIcon />} kind="start" name="Start" type="node_start">
                      <div className="event-plain">Workflow triggered by new chat message.</div>
                    </TraceRow>

                    {(turn.runs.length ? turn.runs : [{ agentName: "Agent", steps: [] }]).map((run, r, runs) => {
                      const isLastRun = r === runs.length - 1;
                      return (
                        <TraceRow
                          key={r}
                          icon={<AgentIcon />}
                          kind="agent"
                          name={run.agentName}
                          type="agent"
                          defaultOpen={isLastRun}
                        >
                          {run.steps.length === 0 && (!turn.isStreaming || !isLastRun) && (
                            <div className="event-plain">No tool calls — answered directly.</div>
                          )}
                          {run.steps.map((step, j) =>
                            step.kind === "tool_call" ? (
                              <div className="trace-event" key={j}>
                                <span className="event-label tool">tool_call</span>
                                <code className="event-code">
                                  {step.name}({JSON.stringify(step.arguments)})
                                </code>
                                {step.result !== undefined && (
                                  <>
                                    <span className="event-label result">node_result</span>
                                    <code className="event-code">{step.result}</code>
                                  </>
                                )}
                              </div>
                            ) : (
                              <div className="event-plain error-text" key={j}>
                                {step.message}
                              </div>
                            )
                          )}
                        </TraceRow>
                      );
                    })}

                    {!turn.isStreaming && !hasError && (
                      <TraceRow icon={<EndIcon />} kind="end" name="End" type="final">
                        <div className="event-plain">Workflow completed.</div>
                      </TraceRow>
                    )}
                  </div>

                  {!hasError && (turn.assistantText || turn.isStreaming) && (
                    <div className="msg-final">
                      {turn.assistantText}
                      {turn.isStreaming && <span className="cursor">▊</span>}
                    </div>
                  )}
                </Fragment>
              );
            })}
          </div>
        )}
      </div>

      <form
        className="run-input"
        onSubmit={(e) => {
          e.preventDefault();
          void sendMessage();
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message the agent…"
          disabled={isSending}
        />
        <button className="send" type="submit" aria-label="Send" disabled={isSending || !input.trim()}>
          <SendIcon />
        </button>
      </form>
    </div>
  );
}

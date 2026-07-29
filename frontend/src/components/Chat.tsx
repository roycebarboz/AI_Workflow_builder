import { useAgentChat } from "../hooks/useAgentChat";

interface ChatProps {
  workflowId: string;
  workflowVersionId: string;
  workflowName: string;
  onBack: () => void;
}

export function Chat({ workflowId, workflowVersionId, workflowName, onBack }: ChatProps) {
  const { turns, input, setInput, sendMessage, isSending } = useAgentChat(
    workflowId,
    workflowVersionId
  );

  return (
    <div className="chat">
      <div className="chat-header">
        <button type="button" className="btn-link" onClick={onBack}>
          ← Workflows
        </button>
        <h2>{workflowName}</h2>
      </div>
      <div className="chat-history">
        {turns.map((turn, i) => (
          <div className="turn" key={i}>
            <div className="message user">{turn.user.content}</div>

            {turn.steps.map((step, j) =>
              step.kind === "tool_call" ? (
                <div className="step tool-call" key={j}>
                  <div className="step-label">
                    🔧 {step.name}({JSON.stringify(step.arguments)})
                  </div>
                  {step.result !== undefined && (
                    <div className="step-result">→ {step.result}</div>
                  )}
                </div>
              ) : (
                <div className="step error" key={j}>
                  ⚠️ {step.message}
                </div>
              )
            )}

            {(turn.assistantText || turn.isStreaming) && (
              <div className="message assistant">
                {turn.assistantText}
                {turn.isStreaming && <span className="cursor">▊</span>}
              </div>
            )}
          </div>
        ))}
      </div>

      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          void sendMessage();
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something…"
          disabled={isSending}
        />
        <button type="submit" disabled={isSending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

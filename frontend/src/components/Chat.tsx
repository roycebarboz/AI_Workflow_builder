import { useState } from "react";
import { streamChat } from "../api/chat";
import type {
  AgentStep,
  ChatMessage,
  ErrorEventData,
  FinalResponseEventData,
  TokenEventData,
  ToolCallResultEventData,
  ToolCallStartEventData,
} from "../types";

interface Turn {
  user: ChatMessage;
  steps: AgentStep[];
  assistantText: string;
  isStreaming: boolean;
}

interface ChatProps {
  workflowId: string;
  workflowName: string;
  onBack: () => void;
}

export function Chat({ workflowId, workflowName, onBack }: ChatProps) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  async function sendMessage() {
    const text = input.trim();
    if (!text || isSending) return;

    const userMessage: ChatMessage = { role: "user", content: text };
    const history: ChatMessage[] = [
      ...turns.flatMap((t): ChatMessage[] =>
        t.assistantText
          ? [t.user, { role: "assistant", content: t.assistantText }]
          : [t.user]
      ),
      userMessage,
    ];

    setInput("");
    setIsSending(true);
    setTurns((prev) => [
      ...prev,
      { user: userMessage, steps: [], assistantText: "", isStreaming: true },
    ]);

    const updateLastTurn = (updater: (turn: Turn) => Turn) => {
      setTurns((prev) => {
        const next = [...prev];
        next[next.length - 1] = updater(next[next.length - 1]);
        return next;
      });
    };

    try {
      for await (const { event, data } of streamChat(workflowId, history)) {
        if (event === "token") {
          const { text: delta } = data as TokenEventData;
          updateLastTurn((t) => ({ ...t, assistantText: t.assistantText + delta }));
        } else if (event === "tool_call_start") {
          const { name, arguments: args } = data as ToolCallStartEventData;
          updateLastTurn((t) => ({
            ...t,
            steps: [...t.steps, { kind: "tool_call", name, arguments: args }],
          }));
        } else if (event === "tool_call_result") {
          const { name, result } = data as ToolCallResultEventData;
          updateLastTurn((t) => ({
            ...t,
            steps: t.steps.map((s, i) =>
              s.kind === "tool_call" && s.name === name && i === t.steps.length - 1
                ? { ...s, result }
                : s
            ),
          }));
        } else if (event === "final_response") {
          const { text: finalText } = data as FinalResponseEventData;
          updateLastTurn((t) => ({ ...t, assistantText: finalText, isStreaming: false }));
        } else if (event === "error") {
          const { message } = data as ErrorEventData;
          updateLastTurn((t) => ({
            ...t,
            steps: [...t.steps, { kind: "error", message }],
            isStreaming: false,
          }));
        }
      }
    } catch (err) {
      updateLastTurn((t) => ({
        ...t,
        steps: [...t.steps, { kind: "error", message: (err as Error).message }],
        isStreaming: false,
      }));
    } finally {
      updateLastTurn((t) => ({ ...t, isStreaming: false }));
      setIsSending(false);
    }
  }

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

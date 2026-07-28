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

export interface Turn {
  user: ChatMessage;
  steps: AgentStep[];
  assistantText: string;
  isStreaming: boolean;
}

/** Drives one workflow's chat turns against the SSE /chat endpoint. Shared
 * by the standalone Chat page and the workflow editor's Run/Preview panel
 * so both render off the same event state machine. */
export function useAgentChat(workflowId: string) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

  function reset() {
    setTurns([]);
    setInput("");
  }

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

  return { turns, input, setInput, sendMessage, isSending, reset };
}

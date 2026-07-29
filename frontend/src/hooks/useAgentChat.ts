import { useRef, useState } from "react";
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

/** One agent node's slice of a turn's trace — tool calls/errors it produced,
 * grouped so the Run panel can label each section with that agent's name. */
export interface AgentRunTrace {
  agentName: string;
  steps: AgentStep[];
}

export interface Turn {
  user: ChatMessage;
  steps: AgentStep[];
  runs: AgentRunTrace[];
  assistantText: string;
  isStreaming: boolean;
}

const DEFAULT_AGENT_NAME = "Agent";

/** Appends to (or starts) the run for `agentName` — the last run in the
 * list if it already belongs to that agent, otherwise a fresh one. */
function withRun(
  runs: AgentRunTrace[],
  agentName: string,
  update: (run: AgentRunTrace) => AgentRunTrace
): AgentRunTrace[] {
  const last = runs[runs.length - 1];
  if (last && last.agentName === agentName) {
    return [...runs.slice(0, -1), update(last)];
  }
  return [...runs, update({ agentName, steps: [] })];
}

/** Updates the last matching pending tool-call step in the last run, mirroring
 * the flat-`steps` update below but scoped to that run's own step list. */
function withResultInLastRun(runs: AgentRunTrace[], name: string, result: string): AgentRunTrace[] {
  if (runs.length === 0) return runs;
  const last = runs[runs.length - 1];
  const steps = last.steps.map((s, i) =>
    s.kind === "tool_call" && s.name === name && i === last.steps.length - 1 ? { ...s, result } : s
  );
  return [...runs.slice(0, -1), { ...last, steps }];
}

/** Drives one workflow's chat turns against the SSE /chat endpoint. Shared
 * by the standalone Chat page and the workflow editor's Run/Preview panel
 * so both render off the same event state machine.
 *
 * `workflowVersionId` pins every turn of this run to the version active
 * when the hook first mounts — captured once into a ref rather than read
 * live off the prop, so a parent re-render with a newer `current_version_id`
 * (e.g. after a save elsewhere) can never retroactively move an in-flight
 * conversation onto a different version. */
export function useAgentChat(workflowId: string, workflowVersionId: string) {
  const pinnedVersionId = useRef(workflowVersionId).current;
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
      { user: userMessage, steps: [], runs: [], assistantText: "", isStreaming: true },
    ]);

    const updateLastTurn = (updater: (turn: Turn) => Turn) => {
      setTurns((prev) => {
        const next = [...prev];
        next[next.length - 1] = updater(next[next.length - 1]);
        return next;
      });
    };

    try {
      for await (const { event, data } of streamChat(workflowId, pinnedVersionId, history)) {
        if (event === "token") {
          const { text: delta, agent_name } = data as TokenEventData;
          const agentName = agent_name ?? DEFAULT_AGENT_NAME;
          updateLastTurn((t) => ({
            ...t,
            assistantText: t.assistantText + delta,
            runs: withRun(t.runs, agentName, (r) => r),
          }));
        } else if (event === "tool_call_start") {
          const { name, arguments: args, agent_name } = data as ToolCallStartEventData;
          const agentName = agent_name ?? DEFAULT_AGENT_NAME;
          updateLastTurn((t) => ({
            ...t,
            steps: [...t.steps, { kind: "tool_call", name, arguments: args }],
            runs: withRun(t.runs, agentName, (r) => ({
              ...r,
              steps: [...r.steps, { kind: "tool_call", name, arguments: args }],
            })),
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
            runs: withResultInLastRun(t.runs, name, result),
          }));
        } else if (event === "final_response") {
          const { text: finalText, agent_name } = data as FinalResponseEventData;
          updateLastTurn((t) => ({
            ...t,
            assistantText: finalText,
            // A null agent_name is the End node's own canned override, not
            // tied to any agent — it replaces the visible answer but isn't
            // a run of its own.
            runs: agent_name ? withRun(t.runs, agent_name, (r) => r) : t.runs,
          }));
        } else if (event === "error") {
          const { message, agent_name } = data as ErrorEventData;
          const agentName = agent_name ?? DEFAULT_AGENT_NAME;
          updateLastTurn((t) => ({
            ...t,
            steps: [...t.steps, { kind: "error", message }],
            runs: withRun(t.runs, agentName, (r) => ({
              ...r,
              steps: [...r.steps, { kind: "error", message }],
            })),
            isStreaming: false,
          }));
        }
      }
    } catch (err) {
      const message = (err as Error).message;
      updateLastTurn((t) => ({
        ...t,
        steps: [...t.steps, { kind: "error", message }],
        runs: withRun(t.runs, DEFAULT_AGENT_NAME, (r) => ({
          ...r,
          steps: [...r.steps, { kind: "error", message }],
        })),
        isStreaming: false,
      }));
    } finally {
      updateLastTurn((t) => ({ ...t, isStreaming: false }));
      setIsSending(false);
    }
  }

  return { turns, input, setInput, sendMessage, isSending, reset };
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export type AgentStep =
  | { kind: "tool_call"; name: string; arguments: unknown; result?: string }
  | { kind: "error"; message: string };

export interface TokenEventData {
  text: string;
}

export interface ToolCallStartEventData {
  name: string;
  arguments: unknown;
}

export interface ToolCallResultEventData {
  name: string;
  result: string;
}

export interface FinalResponseEventData {
  text: string;
}

export interface ErrorEventData {
  message: string;
}

export interface Workflow {
  id: string;
  name: string;
  system_prompt: string;
  enabled_tools: string[];
  created_at: string;
  updated_at: string;
}

export interface ToolInfo {
  name: string;
  description: string;
}

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

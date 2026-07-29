export type GraphNodeType = "start" | "agent" | "condition" | "end";

export interface GraphPosition {
  x: number;
  y: number;
}

export interface AgentNodeData {
  system_prompt: string;
  enabled_tools: string[];
}

export interface ConditionNodeData {
  keyword: string;
}

export interface EndNodeData {
  message?: string;
}

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  position: GraphPosition;
  data: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
}

export interface WorkflowGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Workflow {
  id: string;
  name: string;
  graph: WorkflowGraph;
  system_prompt: string;
  enabled_tools: string[];
  current_version_id: string;
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

export type ExecutionStatus = "running" | "completed" | "error";

export interface ExecutionTranscriptMessage {
  role: string;
  content: string | null;
}

export interface ExecutionToolCall {
  name: string;
  arguments: unknown;
  result: string | null;
}

export interface ExecutionSummary {
  id: string;
  workflow_version_id: string;
  started_at: string;
  status: ExecutionStatus;
  final_response: string | null;
}

export interface ExecutionDetail extends ExecutionSummary {
  transcript: ExecutionTranscriptMessage[];
  tool_calls: ExecutionToolCall[];
  error_message: string | null;
}

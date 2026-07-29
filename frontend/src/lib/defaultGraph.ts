import type {
  AgentNodeData,
  ConditionNodeData,
  GraphNodeType,
  IfElseNodeData,
  StickyNoteNodeData,
  WorkflowGraph,
} from "../types";

export const START_NODE_ID = "start";

// The reserved branch id for an if/else node's fallback edge — matches
// backend/app/schemas.py's ELSE_BRANCH so the two sides can't drift.
export const ELSE_BRANCH = "else";

export function defaultAgentData(): AgentNodeData {
  return { system_prompt: "", enabled_tools: [] };
}

export function defaultConditionData(): ConditionNodeData {
  return { keyword: "" };
}

export function defaultIfElseData(): IfElseNodeData {
  return { branches: [{ id: newBranchId(), label: "If", keyword: "" }] };
}

export function defaultStickyNoteData(): StickyNoteNodeData {
  return { text: "" };
}

let newNodeCounter = 0;

/** Ids for nodes added via canvas drag-and-drop — the Start node is the only
 * one with a well-known fixed id. */
export function newNodeId(type: GraphNodeType): string {
  newNodeCounter += 1;
  return `${type}-${Date.now()}-${newNodeCounter}`;
}

let newBranchCounter = 0;

/** Ids for if/else branches added via the "+ Add branch" button. */
export function newBranchId(): string {
  newBranchCounter += 1;
  return `branch-${Date.now()}-${newBranchCounter}`;
}

export function defaultDataFor(type: GraphNodeType): Record<string, unknown> {
  if (type === "condition") return { ...defaultConditionData() };
  if (type === "agent") return { ...defaultAgentData() };
  if (type === "if_else") return { ...defaultIfElseData() };
  if (type === "sticky_note") return { ...defaultStickyNoteData() };
  return {};
}

/** A new workflow starts with just the required Start node — Agent, Condition,
 * and End are dragged in from the palette to build out the rest. */
export function defaultGraph(): WorkflowGraph {
  return {
    nodes: [{ id: START_NODE_ID, type: "start", position: { x: 40, y: 180 }, data: {} }],
    edges: [],
  };
}

export function agentDataOf(graph: WorkflowGraph): AgentNodeData {
  const data = graph.nodes.find((n) => n.type === "agent")?.data ?? {};
  return {
    system_prompt: typeof data.system_prompt === "string" ? data.system_prompt : "",
    enabled_tools: Array.isArray(data.enabled_tools) ? (data.enabled_tools as string[]) : [],
  };
}

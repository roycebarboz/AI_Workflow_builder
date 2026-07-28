import type { AgentNodeData, ConditionNodeData, GraphNodeType, WorkflowGraph } from "../types";

export const START_NODE_ID = "start";
export const AGENT_NODE_ID = "agent";
export const END_NODE_ID = "end";

export function defaultAgentData(): AgentNodeData {
  return { system_prompt: "", enabled_tools: [] };
}

export function defaultConditionData(): ConditionNodeData {
  return { keyword: "" };
}

let newNodeCounter = 0;

/** Ids for nodes added via canvas drag-and-drop (condition/end branches) — the
 * fixed Start/Agent/End trio above always keeps its own well-known ids. */
export function newNodeId(type: GraphNodeType): string {
  newNodeCounter += 1;
  return `${type}-${Date.now()}-${newNodeCounter}`;
}

export function defaultDataFor(type: GraphNodeType): Record<string, unknown> {
  if (type === "condition") return { ...defaultConditionData() };
  return {};
}

/** Start → Agent → End, the fixed topology ticket 04 supports. */
export function defaultGraph(): WorkflowGraph {
  return {
    nodes: [
      { id: START_NODE_ID, type: "start", position: { x: 40, y: 180 }, data: {} },
      {
        id: AGENT_NODE_ID,
        type: "agent",
        position: { x: 320, y: 150 },
        data: { ...defaultAgentData() },
      },
      { id: END_NODE_ID, type: "end", position: { x: 640, y: 180 }, data: {} },
    ],
    edges: [
      { id: "start-agent", source: START_NODE_ID, target: AGENT_NODE_ID },
      { id: "agent-end", source: AGENT_NODE_ID, target: END_NODE_ID },
    ],
  };
}

export function findAgentNode(graph: WorkflowGraph) {
  const node = graph.nodes.find((n) => n.type === "agent");
  if (!node) throw new Error("Graph is missing its agent node");
  return node;
}

export function agentDataOf(graph: WorkflowGraph): AgentNodeData {
  const data = findAgentNode(graph).data;
  return {
    system_prompt: typeof data.system_prompt === "string" ? data.system_prompt : "",
    enabled_tools: Array.isArray(data.enabled_tools) ? (data.enabled_tools as string[]) : [],
  };
}

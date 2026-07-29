from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .tools.registry import TOOLS

NodeType = Literal["start", "agent", "condition", "end"]

# The two branches a condition node's outgoing edges are tagged with via
# React Flow's `sourceHandle` — shared with agent.py's compiler so the two
# sides can't drift apart on the literal value.
TRUE_BRANCH: Literal["true"] = "true"
FALSE_BRANCH: Literal["false"] = "false"
CONDITION_BRANCHES = {TRUE_BRANCH, FALSE_BRANCH}


class GraphPosition(BaseModel):
    x: float
    y: float


class GraphNode(BaseModel):
    id: str
    type: NodeType
    position: GraphPosition
    data: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: str | None = None


class WorkflowGraph(BaseModel):
    """React Flow's node/edge shape — the same JSON the canvas renders and
    the backend compiles, so there's no separate schema that could drift."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @model_validator(mode="after")
    def _validate_graph(self) -> "WorkflowGraph":
        by_id = {n.id: n for n in self.nodes}
        edges_by_source: dict[str, list[GraphEdge]] = {}
        for edge in self.edges:
            if edge.source not in by_id or edge.target not in by_id:
                raise ValueError(f"Edge '{edge.id}' references an unknown node")
            edges_by_source.setdefault(edge.source, []).append(edge)

        agent_nodes = [n for n in self.nodes if n.type == "agent"]
        if len(agent_nodes) != 1:
            raise ValueError("Graph must contain exactly one agent node")
        agent_node = agent_nodes[0]

        enabled_tools = agent_node.data.get("enabled_tools", [])
        unknown = [t for t in enabled_tools if t not in TOOLS]
        if unknown:
            raise ValueError(f"Unknown tool(s): {', '.join(unknown)}")

        start_nodes = [n for n in self.nodes if n.type == "start"]
        if len(start_nodes) != 1:
            raise ValueError("Graph must contain exactly one start node")
        start_edges = edges_by_source.get(start_nodes[0].id, [])
        if len(start_edges) != 1:
            raise ValueError("Start node must have exactly one outgoing edge")
        if by_id[start_edges[0].target].type not in ("agent", "condition"):
            raise ValueError("Start node must lead to the agent node or a condition node")

        agent_edges = edges_by_source.get(agent_node.id, [])
        if len(agent_edges) != 1:
            raise ValueError("Agent node must have exactly one outgoing edge")
        if by_id[agent_edges[0].target].type != "end":
            raise ValueError("Agent node must lead directly to an end node")

        for node in self.nodes:
            if node.type == "condition":
                keyword = node.data.get("keyword")
                if not isinstance(keyword, str) or not keyword.strip():
                    raise ValueError(f"Condition node '{node.id}' needs a non-empty keyword")
                branch_edges = edges_by_source.get(node.id, [])
                handles = {e.sourceHandle for e in branch_edges}
                if len(branch_edges) != 2 or handles != CONDITION_BRANCHES:
                    raise ValueError(
                        f"Condition node '{node.id}' must have exactly two outgoing edges, "
                        "one from the 'true' handle and one from the 'false' handle"
                    )
            if node.type == "end":
                message = node.data.get("message")
                if message is not None and not isinstance(message, str):
                    raise ValueError(f"End node '{node.id}' message must be a string")

        # A condition branch that bypasses the agent and lands directly on an
        # end node needs a canned message — otherwise that path silently
        # produces no response at all (the agent is what normally supplies one).
        for edge in self.edges:
            if by_id[edge.source].type == "condition" and by_id[edge.target].type == "end":
                if not by_id[edge.target].data.get("message"):
                    raise ValueError(
                        f"End node '{edge.target}' is reached directly from a condition "
                        "branch and needs a non-empty message"
                    )

        return self


def agent_node_data(graph: WorkflowGraph) -> dict:
    return next(n.data for n in graph.nodes if n.type == "agent")


class WorkflowPayload(BaseModel):
    """Shared shape for both create and update requests — a workflow's
    full editable state, since update always replaces it wholesale."""

    name: str = Field(min_length=1)
    graph: WorkflowGraph


WorkflowCreate = WorkflowPayload
WorkflowUpdate = WorkflowPayload


class WorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    graph: WorkflowGraph
    system_prompt: str
    enabled_tools: list[str]
    current_version_id: str
    created_at: datetime
    updated_at: datetime


class ToolInfo(BaseModel):
    name: str
    description: str


class ExecutionTranscriptMessage(BaseModel):
    role: str
    content: str | None = None


class ExecutionToolCall(BaseModel):
    name: str
    arguments: dict
    result: str | None = None


ExecutionStatus = Literal["running", "completed", "error"]


class ExecutionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_version_id: str
    started_at: datetime
    status: ExecutionStatus
    final_response: str | None


class ExecutionDetail(ExecutionSummary):
    transcript: list[ExecutionTranscriptMessage]
    tool_calls: list[ExecutionToolCall]
    error_message: str | None

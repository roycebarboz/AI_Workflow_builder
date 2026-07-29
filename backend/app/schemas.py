from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .tools.registry import TOOLS

NodeType = Literal["start", "agent", "end", "if_else", "sticky_note"]

# The reserved sourceHandle for an if/else node's fallback branch — every
# if/else node has exactly one, alongside its user-defined branch ids.
ELSE_BRANCH: Literal["else"] = "else"


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
        if not agent_nodes:
            raise ValueError("Graph must contain at least one agent node")

        agent_names: list[str] = []
        all_enabled_tools: list[str] = []
        for agent_node in agent_nodes:
            name = agent_node.data.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Agent node '{agent_node.id}' needs a non-empty name")
            agent_names.append(name)

            output_format = agent_node.data.get("output_format")
            if output_format is not None and output_format not in ("text", "json"):
                raise ValueError(
                    f"Agent node '{agent_node.id}' output_format must be 'text' or 'json'"
                )

            all_enabled_tools.extend(agent_node.data.get("enabled_tools", []))

            agent_edges = edges_by_source.get(agent_node.id, [])
            if len(agent_edges) != 1:
                raise ValueError(f"Agent node '{agent_node.id}' must have exactly one outgoing edge")
            if by_id[agent_edges[0].target].type not in ("end", "if_else", "agent"):
                raise ValueError(
                    f"Agent node '{agent_node.id}' must lead to an end node, an if/else node, "
                    "or another agent node"
                )
        if len(agent_names) != len(set(agent_names)):
            raise ValueError("Agent node names must be unique")

        unknown = [t for t in all_enabled_tools if t not in TOOLS]
        if unknown:
            raise ValueError(f"Unknown tool(s): {', '.join(unknown)}")

        start_nodes = [n for n in self.nodes if n.type == "start"]
        if len(start_nodes) != 1:
            raise ValueError("Graph must contain exactly one start node")
        start_edges = edges_by_source.get(start_nodes[0].id, [])
        if len(start_edges) != 1:
            raise ValueError("Start node must have exactly one outgoing edge")
        if by_id[start_edges[0].target].type != "agent":
            raise ValueError("Start node must lead to an agent node")

        for node in self.nodes:
            if node.type == "end":
                message = node.data.get("message")
                if message is not None and not isinstance(message, str):
                    raise ValueError(f"End node '{node.id}' message must be a string")
            if node.type == "if_else":
                branches = node.data.get("branches")
                if not isinstance(branches, list) or not branches:
                    raise ValueError(f"If/else node '{node.id}' needs at least one branch")
                branch_ids: list[str] = []
                for branch in branches:
                    if not isinstance(branch, dict):
                        raise ValueError(f"If/else node '{node.id}' has an invalid branch")
                    branch_id = branch.get("id")
                    label = branch.get("label")
                    keyword = branch.get("keyword")
                    if not isinstance(branch_id, str) or not branch_id.strip():
                        raise ValueError(f"If/else node '{node.id}' has a branch missing an id")
                    if branch_id == ELSE_BRANCH:
                        raise ValueError(
                            f"If/else node '{node.id}' cannot use the reserved id 'else' for a branch"
                        )
                    if not isinstance(label, str) or not label.strip():
                        raise ValueError(
                            f"If/else node '{node.id}' branch '{branch_id}' needs a non-empty label"
                        )
                    if not isinstance(keyword, str) or not keyword.strip():
                        raise ValueError(
                            f"If/else node '{node.id}' branch '{branch_id}' needs a non-empty keyword"
                        )
                    branch_ids.append(branch_id)
                if len(branch_ids) != len(set(branch_ids)):
                    raise ValueError(f"If/else node '{node.id}' has duplicate branch ids")

                branch_edges = edges_by_source.get(node.id, [])
                handles = {e.sourceHandle for e in branch_edges}
                expected = set(branch_ids) | {ELSE_BRANCH}
                if len(branch_edges) != len(expected) or handles != expected:
                    raise ValueError(
                        f"If/else node '{node.id}' must have exactly one outgoing edge per branch, "
                        "plus one from the 'else' handle"
                    )
            if node.type == "sticky_note":
                text = node.data.get("text", "")
                if not isinstance(text, str):
                    raise ValueError(f"Sticky note '{node.id}' text must be a string")

        # If/else nodes only make sense downstream of an agent (they route on
        # its final answer) — only an agent or another if/else node may lead
        # into one, and its branches may lead to an end node, another
        # if/else, or a further agent node.
        for edge in self.edges:
            source_type = by_id[edge.source].type
            target_type = by_id[edge.target].type
            if target_type == "if_else" and source_type not in ("agent", "if_else"):
                raise ValueError(
                    f"Edge '{edge.id}' leads into if/else node '{edge.target}', but only an "
                    "agent node or another if/else node may lead into an if/else node"
                )
            if source_type == "if_else" and target_type not in ("end", "if_else", "agent"):
                raise ValueError(
                    f"If/else node '{edge.source}' must route each branch to an end node, "
                    "another if/else node, or an agent node"
                )
            if source_type == "sticky_note" or target_type == "sticky_note":
                raise ValueError("Sticky notes are decorative and cannot be wired into the graph")

        return self


def agent_node_data(graph: WorkflowGraph) -> dict:
    return next(n.data for n in graph.nodes if n.type == "agent")


def all_enabled_tools(graph: WorkflowGraph) -> list[str]:
    """Union of every agent node's enabled tools, in first-seen order —
    used for the workflow-level denormalized column (list view display),
    since a multi-agent graph's tool usage isn't any single node's alone."""
    seen: dict[str, None] = {}
    for node in graph.nodes:
        if node.type != "agent":
            continue
        for tool in node.data.get("enabled_tools", []):
            seen[tool] = None
    return list(seen)


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

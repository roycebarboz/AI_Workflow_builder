from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .tools.registry import TOOLS

NodeType = Literal["start", "agent", "end"]


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


class WorkflowGraph(BaseModel):
    """React Flow's node/edge shape — the same JSON the canvas renders and
    the backend compiles, so there's no separate schema that could drift."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @field_validator("nodes")
    @classmethod
    def _exactly_one_agent_node(cls, value: list[GraphNode]) -> list[GraphNode]:
        agent_nodes = [n for n in value if n.type == "agent"]
        if len(agent_nodes) != 1:
            raise ValueError("Graph must contain exactly one agent node")

        enabled_tools = agent_nodes[0].data.get("enabled_tools", [])
        unknown = [t for t in enabled_tools if t not in TOOLS]
        if unknown:
            raise ValueError(f"Unknown tool(s): {', '.join(unknown)}")
        return value


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
    created_at: datetime
    updated_at: datetime


class ToolInfo(BaseModel):
    name: str
    description: str

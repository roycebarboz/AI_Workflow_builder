from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Workflow
from .schemas import ToolInfo, WorkflowCreate, WorkflowGraph, WorkflowOut, WorkflowUpdate, agent_node_data
from .tools.registry import TOOLS

router = APIRouter()


def get_workflow_or_404(workflow_id: str, db: Session) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


def _apply_graph(workflow: Workflow, graph: WorkflowGraph) -> None:
    """Writes the graph plus denormalized system_prompt/enabled_tools columns
    used for the workflow list view (see WorkflowsList.tsx) — the LangGraph
    compiler (agent.py) reads the agent node's config straight out of the
    graph itself, so these columns exist for display only."""
    agent_data = agent_node_data(graph)
    workflow.graph = graph.model_dump()
    workflow.system_prompt = agent_data.get("system_prompt", "")
    workflow.enabled_tools = agent_data.get("enabled_tools", [])


@router.post("/workflows", response_model=WorkflowOut, status_code=201)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)) -> Workflow:
    workflow = Workflow(name=payload.name)
    _apply_graph(workflow, payload.graph)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/workflows", response_model=list[WorkflowOut])
def list_workflows(db: Session = Depends(get_db)) -> list[Workflow]:
    return list(db.query(Workflow).order_by(Workflow.created_at.desc()).all())


@router.get("/workflows/{workflow_id}", response_model=WorkflowOut)
def get_workflow(workflow_id: str, db: Session = Depends(get_db)) -> Workflow:
    return get_workflow_or_404(workflow_id, db)


@router.put("/workflows/{workflow_id}", response_model=WorkflowOut)
def update_workflow(
    workflow_id: str, payload: WorkflowUpdate, db: Session = Depends(get_db)
) -> Workflow:
    workflow = get_workflow_or_404(workflow_id, db)
    workflow.name = payload.name
    _apply_graph(workflow, payload.graph)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/tools", response_model=list[ToolInfo])
def list_tools() -> list[ToolInfo]:
    return [
        ToolInfo(name=name, description=spec.schema["function"]["description"])
        for name, spec in TOOLS.items()
    ]

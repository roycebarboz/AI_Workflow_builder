from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models import Workflow, WorkflowVersion
from .schemas import ToolInfo, WorkflowCreate, WorkflowGraph, WorkflowOut, WorkflowUpdate, agent_node_data
from .tools.registry import TOOLS

router = APIRouter()


def get_workflow_or_404(workflow_id: str, db: Session) -> Workflow:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


def get_workflow_version_or_404(
    workflow: Workflow, version_id: str | None, db: Session
) -> WorkflowVersion:
    """Resolves the WorkflowVersion a chat run should execute against:
    the caller-pinned version if given, otherwise the workflow's current
    one. 404s rather than silently falling back if a pinned id doesn't
    belong to this workflow (e.g. stale id from a deleted/other workflow)."""
    target_id = version_id or workflow.current_version_id
    version = db.get(WorkflowVersion, target_id) if target_id else None
    if version is None or version.workflow_id != workflow.id:
        raise HTTPException(status_code=404, detail="Workflow version not found")
    return version


def _apply_graph(workflow: Workflow, graph: WorkflowGraph, db: Session) -> None:
    """Writes a new immutable WorkflowVersion snapshot and points the
    workflow at it, plus the denormalized system_prompt/enabled_tools/graph
    columns used for the workflow list view (see WorkflowsList.tsx) — the
    LangGraph compiler (agent.py) reads a pinned version's own graph at run
    time, so these workflow-level columns exist for display only."""
    agent_data = agent_node_data(graph)
    version = WorkflowVersion(
        workflow_id=workflow.id,
        graph=graph.model_dump(),
        system_prompt=agent_data.get("system_prompt", ""),
        enabled_tools=agent_data.get("enabled_tools", []),
    )
    db.add(version)
    db.flush()  # assigns version.id so workflow.current_version_id can point at it

    workflow.graph = version.graph
    workflow.system_prompt = version.system_prompt
    workflow.enabled_tools = version.enabled_tools
    workflow.current_version_id = version.id


@router.post("/workflows", response_model=WorkflowOut, status_code=201)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)) -> Workflow:
    workflow = Workflow(name=payload.name)
    db.add(workflow)
    db.flush()  # assigns workflow.id so the initial version can reference it
    _apply_graph(workflow, payload.graph, db)
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
    _apply_graph(workflow, payload.graph, db)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/tools", response_model=list[ToolInfo])
def list_tools() -> list[ToolInfo]:
    return [
        ToolInfo(name=name, description=spec.schema["function"]["description"])
        for name, spec in TOOLS.items()
    ]

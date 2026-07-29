from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    graph: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled_tools: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    # Points at the WorkflowVersion currently active for new chat runs. Not a
    # DB-level FK: WorkflowVersion rows are immutable and never deleted, and
    # a plain column here sidesteps a circular FK with workflow_versions.
    current_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class WorkflowVersion(Base):
    """Immutable snapshot of a workflow's graph/system_prompt/enabled_tools,
    written on every save. A chat run pins to one of these (see
    `main.get_workflow_version_or_404`) so editing the workflow afterward
    never changes behavior already in flight."""

    __tablename__ = "workflow_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    workflow_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflows.id"), nullable=False
    )
    graph: Mapped[dict] = mapped_column(JSON, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled_tools: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ExecutionRecord(Base):
    """One chat run, pinned to the WorkflowVersion active when it started.
    Written incrementally as the run progresses (see app.executions) so a
    run that errors or is interrupted mid-stream still leaves a visible
    history entry rather than only appearing on clean completion."""

    __tablename__ = "execution_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    workflow_version_id: Mapped[str] = mapped_column(
        String, ForeignKey("workflow_versions.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    transcript: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    tool_calls: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

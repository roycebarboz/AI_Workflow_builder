from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .tools.registry import TOOLS


class WorkflowPayload(BaseModel):
    """Shared shape for both create and update requests — a workflow's
    full editable state, since update always replaces it wholesale."""

    name: str = Field(min_length=1)
    system_prompt: str = ""
    enabled_tools: list[str] = Field(default_factory=list)

    @field_validator("enabled_tools")
    @classmethod
    def _tools_must_be_known(cls, value: list[str]) -> list[str]:
        unknown = [name for name in value if name not in TOOLS]
        if unknown:
            raise ValueError(f"Unknown tool(s): {', '.join(unknown)}")
        return value


WorkflowCreate = WorkflowPayload
WorkflowUpdate = WorkflowPayload


class WorkflowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    system_prompt: str
    enabled_tools: list[str]
    created_at: datetime
    updated_at: datetime


class ToolInfo(BaseModel):
    name: str
    description: str

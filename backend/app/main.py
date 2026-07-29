from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker
from sse_starlette.sse import EventSourceResponse

load_dotenv()

from .agent import (
    AgentEvent,
    ErrorEvent,
    FinalResponseEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    TokenEvent,
    run_agent_loop,
)
from .db import get_db, get_session_factory
from .executions import ExecutionRecorder
from .llm import LLMClient, OpenAILLMClient
from .workflows_api import get_workflow_or_404, get_workflow_version_or_404
from .workflows_api import router as workflows_router

app = FastAPI(title="AI Workflow Builder — backend")
app.include_router(workflows_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_llm_client() -> LLMClient:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    return OpenAILLMClient(client=client, model=model)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    workflow_id: str
    # Pins the run to the WorkflowVersion active when the chat started; the
    # frontend captures this once per conversation (see useAgentChat) and
    # resends it on every turn so a later workflow edit can't retroactively
    # change an in-flight run. Omitted, it falls back to the workflow's
    # current version — used by callers that don't pin (e.g. tests).
    workflow_version_id: str | None = None
    messages: list[ChatMessage] = Field(min_length=1)


def _to_sse(event: AgentEvent) -> dict:
    if isinstance(event, TokenEvent):
        return {"event": "token", "data": json.dumps({"text": event.text})}
    if isinstance(event, ToolCallStartEvent):
        return {
            "event": "tool_call_start",
            "data": json.dumps({"name": event.name, "arguments": event.arguments}),
        }
    if isinstance(event, ToolCallResultEvent):
        return {
            "event": "tool_call_result",
            "data": json.dumps({"name": event.name, "result": event.result}),
        }
    if isinstance(event, FinalResponseEvent):
        return {"event": "final_response", "data": json.dumps({"text": event.text})}
    if isinstance(event, ErrorEvent):
        return {"event": "error", "data": json.dumps({"message": event.message})}
    raise ValueError(f"Unknown agent event type: {event!r}")


@app.post("/chat")
def chat(
    request: ChatRequest,
    llm_client: LLMClient = Depends(get_llm_client),
    db: Session = Depends(get_db),
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
):
    workflow = get_workflow_or_404(request.workflow_id, db)
    version = get_workflow_version_or_404(workflow, request.workflow_version_id, db)

    history = [m.model_dump() for m in request.messages]
    graph = version.graph
    workflow_version_id = version.id

    def event_stream():
        with session_factory() as exec_db:
            recorder = ExecutionRecorder(exec_db, workflow_version_id, history)
            for event in run_agent_loop(llm_client, graph, history):
                recorder.on_event(event)
                yield _to_sse(event)

    return EventSourceResponse(event_stream())


@app.get("/health")
def health():
    return {"status": "ok"}

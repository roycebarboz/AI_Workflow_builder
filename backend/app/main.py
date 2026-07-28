from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field
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
from .llm import LLMClient, OpenAILLMClient

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a calculator tool. "
    "Use it whenever exact arithmetic matters instead of guessing."
)

app = FastAPI(title="AI Workflow Builder — backend")

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
def chat(request: ChatRequest, llm_client: LLMClient = Depends(get_llm_client)):
    history = [m.model_dump() for m in request.messages]

    def event_stream():
        for event in run_agent_loop(llm_client, SYSTEM_PROMPT, history):
            yield _to_sse(event)

    return EventSourceResponse(event_stream())


@app.get("/health")
def health():
    return {"status": "ok"}

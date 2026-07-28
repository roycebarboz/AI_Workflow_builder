"""LangGraph StateGraph that drives an LLMClient through rounds of tool
calls until it produces a final answer, streaming normalized events the
/chat endpoint turns into SSE.

One Agent node calls the LLM and either finishes or requests tool calls;
a Tools node executes any requested tool calls and loops back to the
Agent node. Both nodes emit events via LangGraph's custom stream mode
(`get_stream_writer`), which `run_agent_loop` forwards as-is.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from typing import Iterator, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .llm import ContentDelta, LLMClient, StreamDone, ToolCallRequest
from .tools.registry import TOOLS, tool_schemas

MAX_ROUNDS = 8


@dataclass(frozen=True)
class TokenEvent:
    text: str


@dataclass(frozen=True)
class ToolCallStartEvent:
    name: str
    arguments: dict


@dataclass(frozen=True)
class ToolCallResultEvent:
    name: str
    result: str


@dataclass(frozen=True)
class FinalResponseEvent:
    text: str


@dataclass(frozen=True)
class ErrorEvent:
    message: str


AgentEvent = TokenEvent | ToolCallStartEvent | ToolCallResultEvent | FinalResponseEvent | ErrorEvent


class GraphState(TypedDict):
    messages: list[dict]
    pending_tool_calls: list[ToolCallRequest]
    round: int
    failed: bool


def _agent_node(state: GraphState, *, llm_client: LLMClient, tools: list[dict]) -> dict:
    writer = get_stream_writer()
    messages = state["messages"]
    round_ = state["round"] + 1

    if round_ > MAX_ROUNDS:
        writer(ErrorEvent(message="Agent exceeded maximum tool-call rounds without a final answer."))
        return {"round": round_, "failed": True, "pending_tool_calls": []}

    content_parts: list[str] = []
    tool_calls: list[ToolCallRequest] = []
    finish_reason = "stop"

    try:
        for event in llm_client.stream_chat(messages, tools):
            if isinstance(event, ContentDelta):
                content_parts.append(event.text)
                writer(TokenEvent(text=event.text))
            elif isinstance(event, ToolCallRequest):
                tool_calls.append(event)
            elif isinstance(event, StreamDone):
                finish_reason = event.finish_reason
    except Exception as exc:  # external API boundary
        writer(ErrorEvent(message=str(exc)))
        return {"round": round_, "failed": True, "pending_tool_calls": []}

    content = "".join(content_parts)

    if finish_reason != "tool_calls" or not tool_calls:
        writer(FinalResponseEvent(text=content))
        return {"round": round_, "pending_tool_calls": []}

    assistant_message = {
        "role": "assistant",
        "content": content or None,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": tc.arguments},
            }
            for tc in tool_calls
        ],
    }

    return {
        "round": round_,
        "messages": [*messages, assistant_message],
        "pending_tool_calls": tool_calls,
    }


def _tools_node(state: GraphState) -> dict:
    writer = get_stream_writer()
    messages = list(state["messages"])

    for tc in state["pending_tool_calls"]:
        try:
            args = json.loads(tc.arguments) if tc.arguments else {}
        except json.JSONDecodeError:
            args = {}

        writer(ToolCallStartEvent(name=tc.name, arguments=args))

        spec = TOOLS.get(tc.name)
        try:
            result = spec.fn(**args) if spec else f"Error: unknown tool '{tc.name}'"
        except Exception as exc:  # tool implementations are untrusted boundary code
            writer(ErrorEvent(message=f"Tool '{tc.name}' failed: {exc}"))
            return {"messages": messages, "pending_tool_calls": [], "failed": True}

        writer(ToolCallResultEvent(name=tc.name, result=result))
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return {"messages": messages, "pending_tool_calls": []}


def _route_after_agent(state: GraphState) -> str:
    if state["failed"] or not state["pending_tool_calls"]:
        return END
    return "tools"


def _route_after_tools(state: GraphState) -> str:
    return END if state["failed"] else "agent"


def _build_graph(llm_client: LLMClient, tools: list[dict]) -> CompiledStateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("agent", functools.partial(_agent_node, llm_client=llm_client, tools=tools))
    graph.add_node("tools", _tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _route_after_agent, {"tools": "tools", END: END})
    graph.add_conditional_edges("tools", _route_after_tools, {"agent": "agent", END: END})
    return graph.compile()


def run_agent_loop(
    llm_client: LLMClient,
    system_prompt: str,
    history: list[dict],
    enabled_tools: list[str] | None = None,
) -> Iterator[AgentEvent]:
    messages: list[dict] = [{"role": "system", "content": system_prompt}, *history]
    tools = tool_schemas(enabled_tools)
    graph = _build_graph(llm_client, tools)

    initial_state: GraphState = {
        "messages": messages,
        "pending_tool_calls": [],
        "round": 0,
        "failed": False,
    }

    yield from graph.stream(initial_state, stream_mode="custom")

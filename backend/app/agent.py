"""LangGraph StateGraph that drives an LLMClient through rounds of tool
calls until it produces a final answer, streaming normalized events the
/chat endpoint turns into SSE.

The Agent node calls the LLM and either finishes or requests tool calls;
a Tools node executes any requested tool calls and loops back to the
Agent node. Once the agent stops calling tools, routing continues along
whatever the workflow's graph wires downstream of the agent node —
directly to an end, through user-defined condition nodes that gate entry
to the agent, or through if/else nodes that branch on the agent's final
answer (see `_build_graph`). All nodes emit events via LangGraph's custom
stream mode (`get_stream_writer`), which `run_agent_loop` forwards as-is.
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
from .schemas import ELSE_BRANCH, FALSE_BRANCH, TRUE_BRANCH
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
    route: str
    final_response: str


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
        return {"round": round_, "pending_tool_calls": [], "final_response": content}

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


def _condition_node(state: GraphState, *, keyword: str) -> dict:
    last_user = next(
        (m["content"] for m in reversed(state["messages"]) if m.get("role") == "user"), ""
    )
    matched = keyword.lower() in (last_user or "").lower()
    return {"route": TRUE_BRANCH if matched else FALSE_BRANCH}


def _if_else_node(state: GraphState, *, branches: list[tuple[str, str]]) -> dict:
    output = (state.get("final_response") or "").lower()
    for branch_id, keyword in branches:
        if keyword.lower() in output:
            return {"route": branch_id}
    return {"route": ELSE_BRANCH}


def _end_node(state: GraphState, *, message: str) -> dict:
    writer = get_stream_writer()
    writer(FinalResponseEvent(text=message))
    return {}


def _route_after_agent_tools(state: GraphState) -> str:
    if state["failed"]:
        return "error"
    return "tools" if state["pending_tool_calls"] else "downstream"


def _route_after_tools(state: GraphState) -> str:
    return END if state["failed"] else "agent"


def _route_condition(state: GraphState) -> str:
    return state["route"]


def _build_graph(llm_client: LLMClient, tools: list[dict], graph: dict) -> CompiledStateGraph:
    """Compiles the workflow's node/edge graph into a LangGraph StateGraph.

    The Agent node is always a fixed agent+tools tool-call loop (there's
    exactly one, enforced by WorkflowGraph validation). Condition and if/else
    nodes are compiled into real nodes with conditional edges, resolved
    recursively so a chain of conditions/if-elses or a direct wire straight
    to an end all work the same way. `resolve` is called lazily per node id
    and memoizes results so a node shared by multiple incoming edges is only
    added once.
    """
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    edges_by_source: dict[str, list[dict]] = {}
    for edge in graph["edges"]:
        edges_by_source.setdefault(edge["source"], []).append(edge)

    state_graph = StateGraph(GraphState)
    state_graph.add_node("agent", functools.partial(_agent_node, llm_client=llm_client, tools=tools))
    state_graph.add_node("tools", _tools_node)
    state_graph.add_conditional_edges("tools", _route_after_tools, {"agent": "agent", END: END})

    compiled: dict[str, str] = {}

    def resolve(node_id: str) -> str:
        if node_id in compiled:
            return compiled[node_id]

        node = nodes_by_id[node_id]
        node_type = node["type"]

        if node_type == "agent":
            compiled[node_id] = "agent"
            return "agent"

        if node_type == "end":
            message = node["data"].get("message")
            if not message:
                compiled[node_id] = END
                return END
            name = f"end_{node_id}"
            compiled[node_id] = name
            state_graph.add_node(name, functools.partial(_end_node, message=message))
            state_graph.add_edge(name, END)
            return name

        if node_type == "condition":
            name = f"cond_{node_id}"
            compiled[node_id] = name
            keyword = node["data"]["keyword"]
            state_graph.add_node(name, functools.partial(_condition_node, keyword=keyword))
            branches = {e["sourceHandle"]: e["target"] for e in edges_by_source[node_id]}
            state_graph.add_conditional_edges(
                name,
                _route_condition,
                {
                    TRUE_BRANCH: resolve(branches[TRUE_BRANCH]),
                    FALSE_BRANCH: resolve(branches[FALSE_BRANCH]),
                },
            )
            return name

        if node_type == "if_else":
            name = f"ifelse_{node_id}"
            compiled[node_id] = name
            branch_defs = [(b["id"], b["keyword"]) for b in node["data"]["branches"]]
            state_graph.add_node(name, functools.partial(_if_else_node, branches=branch_defs))
            branch_targets = {e["sourceHandle"]: e["target"] for e in edges_by_source[node_id]}
            routes = {branch_id: resolve(branch_targets[branch_id]) for branch_id, _ in branch_defs}
            routes[ELSE_BRANCH] = resolve(branch_targets[ELSE_BRANCH])
            state_graph.add_conditional_edges(name, _route_condition, routes)
            return name

        raise ValueError(f"Cannot route through node type '{node_type}'")

    agent_node_id = next(n["id"] for n in graph["nodes"] if n["type"] == "agent")
    start_node_id = next(n["id"] for n in graph["nodes"] if n["type"] == "start")

    agent_downstream = resolve(edges_by_source[agent_node_id][0]["target"])
    state_graph.add_conditional_edges(
        "agent", _route_after_agent_tools, {"tools": "tools", "downstream": agent_downstream, "error": END}
    )
    state_graph.set_entry_point(resolve(edges_by_source[start_node_id][0]["target"]))

    return state_graph.compile()


def run_agent_loop(
    llm_client: LLMClient,
    graph: dict,
    history: list[dict],
) -> Iterator[AgentEvent]:
    agent_data = next(n["data"] for n in graph["nodes"] if n["type"] == "agent")
    system_prompt = agent_data.get("system_prompt", "")
    enabled_tools = agent_data.get("enabled_tools", [])

    messages: list[dict] = [{"role": "system", "content": system_prompt}, *history]
    tools = tool_schemas(enabled_tools)
    compiled_graph = _build_graph(llm_client, tools, graph)

    initial_state: GraphState = {
        "messages": messages,
        "pending_tool_calls": [],
        "round": 0,
        "failed": False,
        "route": "",
        "final_response": "",
    }

    yield from compiled_graph.stream(initial_state, stream_mode="custom")

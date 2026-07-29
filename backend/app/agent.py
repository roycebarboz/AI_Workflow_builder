"""LangGraph StateGraph that drives one or more agent nodes through rounds
of tool calls until each produces a final answer, streaming normalized
events the /chat endpoint turns into SSE.

Each agent node in the workflow graph compiles to its own Agent+Tools node
pair, using that node's own system prompt, enabled tools, and output
format (see `_build_graph`). An agent node calls the LLM and either
finishes or requests tool calls; its paired Tools node executes any
requested tool calls and loops back. Once an agent stops calling tools,
routing continues along whatever the workflow's graph wires downstream —
directly to an end, into another agent node, or through an if/else node
that branches on that agent's final answer. All nodes emit events via
LangGraph's custom stream mode (`get_stream_writer`), which
`run_agent_loop` forwards as-is.
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
from .schemas import ELSE_BRANCH
from .tools.registry import TOOLS, tool_schemas

MAX_ROUNDS = 8


@dataclass(frozen=True)
class TokenEvent:
    text: str
    agent_name: str | None = None


@dataclass(frozen=True)
class ToolCallStartEvent:
    name: str
    arguments: dict
    agent_name: str | None = None


@dataclass(frozen=True)
class ToolCallResultEvent:
    name: str
    result: str
    agent_name: str | None = None


@dataclass(frozen=True)
class FinalResponseEvent:
    text: str
    # None for the fixed message an End node emits directly (not produced by
    # any agent) — set to the originating agent's name everywhere else.
    agent_name: str | None = None


@dataclass(frozen=True)
class ErrorEvent:
    message: str
    agent_name: str | None = None


AgentEvent = TokenEvent | ToolCallStartEvent | ToolCallResultEvent | FinalResponseEvent | ErrorEvent


class GraphState(TypedDict):
    messages: list[dict]
    pending_tool_calls: list[ToolCallRequest]
    rounds: dict[str, int]
    failed: bool
    route: str
    final_response: str


def _agent_node(
    state: GraphState,
    *,
    llm_client: LLMClient,
    tools: list[dict],
    system_prompt: str,
    response_format: dict | None,
    node_id: str,
    agent_name: str,
) -> dict:
    writer = get_stream_writer()
    history = state["messages"]
    rounds = dict(state["rounds"])
    round_ = rounds.get(node_id, 0) + 1
    rounds[node_id] = round_

    if round_ > MAX_ROUNDS:
        writer(
            ErrorEvent(
                message="Agent exceeded maximum tool-call rounds without a final answer.",
                agent_name=agent_name,
            )
        )
        return {"rounds": rounds, "failed": True, "pending_tool_calls": []}

    messages = [{"role": "system", "content": system_prompt}, *history]
    content_parts: list[str] = []
    tool_calls: list[ToolCallRequest] = []
    finish_reason = "stop"

    try:
        for event in llm_client.stream_chat(messages, tools, response_format=response_format):
            if isinstance(event, ContentDelta):
                content_parts.append(event.text)
                writer(TokenEvent(text=event.text, agent_name=agent_name))
            elif isinstance(event, ToolCallRequest):
                tool_calls.append(event)
            elif isinstance(event, StreamDone):
                finish_reason = event.finish_reason
    except Exception as exc:  # external API boundary
        writer(ErrorEvent(message=str(exc), agent_name=agent_name))
        return {"rounds": rounds, "failed": True, "pending_tool_calls": []}

    content = "".join(content_parts)

    if finish_reason != "tool_calls" or not tool_calls:
        writer(FinalResponseEvent(text=content, agent_name=agent_name))
        return {
            "rounds": rounds,
            "pending_tool_calls": [],
            "final_response": content,
            "messages": [*history, {"role": "assistant", "content": content}],
        }

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
        "rounds": rounds,
        "messages": [*history, assistant_message],
        "pending_tool_calls": tool_calls,
    }


def _tools_node(state: GraphState, *, agent_name: str) -> dict:
    writer = get_stream_writer()
    messages = list(state["messages"])

    for tc in state["pending_tool_calls"]:
        try:
            args = json.loads(tc.arguments) if tc.arguments else {}
        except json.JSONDecodeError:
            args = {}

        writer(ToolCallStartEvent(name=tc.name, arguments=args, agent_name=agent_name))

        spec = TOOLS.get(tc.name)
        try:
            result = spec.fn(**args) if spec else f"Error: unknown tool '{tc.name}'"
        except Exception as exc:  # tool implementations are untrusted boundary code
            writer(ErrorEvent(message=f"Tool '{tc.name}' failed: {exc}", agent_name=agent_name))
            return {"messages": messages, "pending_tool_calls": [], "failed": True}

        writer(ToolCallResultEvent(name=tc.name, result=result, agent_name=agent_name))
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return {"messages": messages, "pending_tool_calls": []}


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


def _build_graph(llm_client: LLMClient, graph: dict) -> CompiledStateGraph:
    """Compiles the workflow's node/edge graph into a LangGraph StateGraph.

    Each agent node compiles to its own agent+tools tool-call loop, using
    that node's own system prompt, enabled tools, and output format. If/else
    nodes are compiled into real nodes with conditional edges. `resolve` is
    called lazily per node id and memoizes results so a node shared by
    multiple incoming edges (or reachable via more than one path) is only
    added once, and so a chain of agents/if-elses or a direct wire straight
    to an end all work the same way.
    """
    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    edges_by_source: dict[str, list[dict]] = {}
    for edge in graph["edges"]:
        edges_by_source.setdefault(edge["source"], []).append(edge)

    state_graph = StateGraph(GraphState)
    compiled: dict[str, str] = {}

    def resolve(node_id: str) -> str:
        if node_id in compiled:
            return compiled[node_id]

        node = nodes_by_id[node_id]
        node_type = node["type"]

        if node_type == "agent":
            name = f"agent_{node_id}"
            tools_name = f"tools_{node_id}"
            compiled[node_id] = name
            data = node["data"]
            agent_name = data.get("name") or "Agent"
            system_prompt = data.get("system_prompt", "")
            output_format = data.get("output_format")
            response_format: dict | None = None
            if output_format == "json":
                response_format = {"type": "json_object"}
                system_prompt = f"{system_prompt}\n\nRespond only with a single valid JSON object."
            tools = tool_schemas(data.get("enabled_tools", []))
            state_graph.add_node(
                name,
                functools.partial(
                    _agent_node,
                    llm_client=llm_client,
                    tools=tools,
                    system_prompt=system_prompt,
                    response_format=response_format,
                    node_id=node_id,
                    agent_name=agent_name,
                ),
            )
            state_graph.add_node(tools_name, functools.partial(_tools_node, agent_name=agent_name))
            downstream = resolve(edges_by_source[node_id][0]["target"])
            state_graph.add_conditional_edges(
                name,
                _route_after_agent_tools,
                {"tools": tools_name, "downstream": downstream, "error": END},
            )
            state_graph.add_conditional_edges(tools_name, _route_after_tools, {"agent": name, END: END})
            return name

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

    start_node_id = next(n["id"] for n in graph["nodes"] if n["type"] == "start")
    state_graph.set_entry_point(resolve(edges_by_source[start_node_id][0]["target"]))

    return state_graph.compile()


def run_agent_loop(
    llm_client: LLMClient,
    graph: dict,
    history: list[dict],
) -> Iterator[AgentEvent]:
    compiled_graph = _build_graph(llm_client, graph)

    initial_state: GraphState = {
        "messages": list(history),
        "pending_tool_calls": [],
        "rounds": {},
        "failed": False,
        "route": "",
        "final_response": "",
    }

    yield from compiled_graph.stream(initial_state, stream_mode="custom")

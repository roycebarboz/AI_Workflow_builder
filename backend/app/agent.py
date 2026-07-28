"""Agent loop: drives an LLMClient through rounds of tool calls until it
produces a final answer, yielding normalized events the /chat endpoint
turns into SSE.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator

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


def run_agent_loop(
    llm_client: LLMClient,
    system_prompt: str,
    history: list[dict],
    enabled_tools: list[str] | None = None,
) -> Iterator[AgentEvent]:
    messages: list[dict] = [{"role": "system", "content": system_prompt}, *history]
    tools = tool_schemas(enabled_tools)

    for _ in range(MAX_ROUNDS):
        content_parts: list[str] = []
        tool_calls: list[ToolCallRequest] = []
        finish_reason = "stop"

        try:
            for event in llm_client.stream_chat(messages, tools):
                if isinstance(event, ContentDelta):
                    content_parts.append(event.text)
                    yield TokenEvent(text=event.text)
                elif isinstance(event, ToolCallRequest):
                    tool_calls.append(event)
                elif isinstance(event, StreamDone):
                    finish_reason = event.finish_reason
        except Exception as exc:  # external API boundary
            yield ErrorEvent(message=str(exc))
            return

        content = "".join(content_parts)

        if finish_reason != "tool_calls" or not tool_calls:
            yield FinalResponseEvent(text=content)
            return

        messages.append(
            {
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
        )

        for tc in tool_calls:
            try:
                args = json.loads(tc.arguments) if tc.arguments else {}
            except json.JSONDecodeError:
                args = {}

            yield ToolCallStartEvent(name=tc.name, arguments=args)

            spec = TOOLS.get(tc.name)
            result = spec.fn(**args) if spec else f"Error: unknown tool '{tc.name}'"

            yield ToolCallResultEvent(name=tc.name, result=result)

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    yield ErrorEvent(message="Agent exceeded maximum tool-call rounds without a final answer.")

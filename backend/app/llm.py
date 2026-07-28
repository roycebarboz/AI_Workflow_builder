"""Thin normalized wrapper around the OpenAI streaming chat API.

This is the one seam that touches the real external API. Everything
above this module (the agent loop, the /chat endpoint) only ever sees
the normalized event types below, so tests stub `LLMClient` here
instead of reaching into the OpenAI SDK's chunk format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal, Protocol

from openai import OpenAI


@dataclass(frozen=True)
class ContentDelta:
    text: str


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: str  # raw JSON string, full accumulated arguments


@dataclass(frozen=True)
class StreamDone:
    finish_reason: Literal["stop", "tool_calls"]


LLMStreamEvent = ContentDelta | ToolCallRequest | StreamDone


class LLMClient(Protocol):
    def stream_chat(self, messages: list[dict], tools: list[dict]) -> Iterator[LLMStreamEvent]:
        ...


@dataclass
class _PendingToolCall:
    id: str = ""
    name: str = ""
    arguments: str = ""


class OpenAILLMClient:
    def __init__(self, client: OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def stream_chat(self, messages: list[dict], tools: list[dict]) -> Iterator[LLMStreamEvent]:
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools,
            stream=True,
        )

        pending_calls: dict[int, _PendingToolCall] = {}
        finish_reason: str | None = None

        for chunk in stream:
            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason

            if delta.content:
                yield ContentDelta(text=delta.content)

            for tc in delta.tool_calls or []:
                pending = pending_calls.setdefault(tc.index, _PendingToolCall())
                if tc.id:
                    pending.id = tc.id
                if tc.function and tc.function.name:
                    pending.name += tc.function.name
                if tc.function and tc.function.arguments:
                    pending.arguments += tc.function.arguments

        for pending in pending_calls.values():
            yield ToolCallRequest(id=pending.id, name=pending.name, arguments=pending.arguments)

        yield StreamDone(finish_reason=finish_reason or "stop")

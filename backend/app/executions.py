"""Persists an ExecutionRecord as a chat run's agent events stream by,
rather than only writing on clean completion — so an errored or
interrupted run still leaves a visible history entry (see 07 —
Execution history). Runs on its own DB session (see
`db.get_session_factory`) because the request-scoped `Depends(get_db)`
session is already closed by the time an SSE generator body executes.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .agent import AgentEvent, ErrorEvent, FinalResponseEvent, ToolCallResultEvent, ToolCallStartEvent
from .models import ExecutionRecord


class ExecutionRecorder:
    def __init__(self, db: Session, workflow_version_id: str, history: list[dict]) -> None:
        self._db = db
        self.record = ExecutionRecord(
            workflow_version_id=workflow_version_id,
            transcript=list(history),
            tool_calls=[],
            status="running",
        )
        db.add(self.record)
        db.commit()

    def on_event(self, event: AgentEvent) -> None:
        if isinstance(event, ToolCallStartEvent):
            self.record.tool_calls = [
                *self.record.tool_calls,
                {"name": event.name, "arguments": event.arguments, "result": None},
            ]
        elif isinstance(event, ToolCallResultEvent):
            tool_calls = list(self.record.tool_calls)
            for i in range(len(tool_calls) - 1, -1, -1):
                if tool_calls[i]["name"] == event.name and tool_calls[i]["result"] is None:
                    tool_calls[i] = {**tool_calls[i], "result": event.result}
                    break
            self.record.tool_calls = tool_calls
        elif isinstance(event, FinalResponseEvent):
            self.record.final_response = event.text
            self.record.status = "completed"
            self.record.transcript = [
                *self.record.transcript,
                {"role": "assistant", "content": event.text},
            ]
        elif isinstance(event, ErrorEvent):
            self.record.status = "error"
            self.record.error_message = event.message
        else:
            return  # TokenEvent: too chatty to persist per-delta

        self._db.commit()

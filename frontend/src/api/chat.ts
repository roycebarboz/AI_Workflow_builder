import type { ChatMessage } from "../types";

export interface ChatSSEEvent {
  event: string;
  data: unknown;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function parseBlock(block: string): ChatSSEEvent | null {
  let eventType = "message";
  let dataLine = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLine += line.slice("data:".length).trim();
    }
  }
  if (!dataLine) return null;
  try {
    return { event: eventType, data: JSON.parse(dataLine) };
  } catch {
    return null;
  }
}

/** Streams a chat turn, yielding one normalized SSE event at a time. */
export async function* streamChat(
  workflowId: string,
  messages: ChatMessage[]
): AsyncGenerator<ChatSSEEvent> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ workflow_id: workflowId, messages }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let separatorIndex: number;
    while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, separatorIndex);
      buffer = buffer.slice(separatorIndex + 2);
      const event = parseBlock(block);
      if (event) yield event;
    }
  }
}

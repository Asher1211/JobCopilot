/** Utilities for reading Server-Sent Events from a ReadableStream. */

type SseHandler = (event: string, data: unknown) => void;

export async function readSSE(
  stream: ReadableStream<Uint8Array>,
  handler: SseHandler,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
        continue;
      }
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6);
      if (!raw || raw === "{}" || raw === "[DONE]") continue;

      try {
        handler(currentEvent, JSON.parse(raw));
      } catch {
        // Skip unparseable events
      }
    }
  }
}

/** Fetch + SSE: POST JSON, stream response, call handler per event. */
export async function fetchSSE(
  url: string,
  body: unknown,
  handler: SseHandler,
  token?: string | null,
): Promise<void> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  const stream = res.body;
  if (!stream) throw new Error("No response stream");
  return readSSE(stream, handler);
}

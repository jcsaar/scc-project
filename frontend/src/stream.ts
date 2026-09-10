import type { ProgressEvent, WorkflowResult } from "./types";

export type StreamHandlers = {
  onProgress: (event: ProgressEvent) => void;
  onResult: (result: WorkflowResult) => void;
};

type StreamRecord = { type: "progress" | "result" | "error"; data: unknown };

function parseFrame(frame: string): StreamRecord | null {
  const lines = frame.split("\n");
  const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
  const data = lines.find((line) => line.startsWith("data: "))?.slice(6);
  if (!event || data === undefined) return null;
  return { type: event as StreamRecord["type"], data: JSON.parse(data) };
}

export async function consumeSse(
  response: Response,
  handlers: StreamHandlers,
): Promise<WorkflowResult> {
  if (!response.ok || !response.body) throw new Error("Live workflow stream unavailable");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: WorkflowResult | null = null;
  while (true) {
    const chunk = await reader.read();
    buffer += decoder.decode(chunk.value ?? new Uint8Array(), { stream: !chunk.done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const record = parseFrame(frame);
      if (!record) continue;
      if (record.type === "progress") handlers.onProgress(record.data as ProgressEvent);
      else if (record.type === "result") {
        result = record.data as WorkflowResult;
        handlers.onResult(result);
      } else throw new Error((record.data as { detail?: string }).detail ?? "Workflow failed");
    }
    if (chunk.done) break;
  }
  if (!result) throw new Error("Workflow ended without a result");
  return result;
}

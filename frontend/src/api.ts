import type { DemoMode, WorkflowResult } from "./types";
import { consumeSse } from "./stream";

async function checked<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function streamWorkflow(
  input: {
    employeeId: string;
    mode: DemoMode;
    provider: string;
    prompt: string;
  },
  handlers: Parameters<typeof consumeSse>[1],
  signal?: AbortSignal,
): Promise<WorkflowResult> {
  const session = await checked<{ id: string }>(
    await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee_id: input.employeeId,
        mode: input.mode,
        trust_zone_id: input.provider,
        project_id: "project-aurora",
      }),
      signal,
    }),
  );
  return consumeSse(
    await fetch(`/api/sessions/${session.id}/run-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: input.prompt }),
      signal,
    }),
    handlers,
  );
}

export async function resetDemo(): Promise<void> {
  await checked(
    await fetch("/api/demo/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmation: "RESET SYNTHETIC DEMO" }),
    }),
  );
}

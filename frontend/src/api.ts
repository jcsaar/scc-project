import type { DemoMode, ScenarioResult, WorkflowResult } from "./types";

async function checked<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function runWorkflow(input: {
  employeeId: string;
  mode: DemoMode;
  provider: string;
  prompt: string;
}): Promise<WorkflowResult> {
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
    }),
  );
  return checked<WorkflowResult>(
    await fetch(`/api/sessions/${session.id}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: input.prompt }),
    }),
  );
}

export async function runScenario(id: string): Promise<ScenarioResult> {
  return checked<ScenarioResult>(
    await fetch(`/api/demo/scenarios/${id}/run`, { method: "POST" }),
  );
}

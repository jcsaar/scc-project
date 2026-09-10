import type {
  DemoMode,
  LedgerClaim,
  Policy,
  ScenarioResult,
  WorkflowResult,
} from "./types";
import { consumeSse } from "./stream";

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

export async function runScenario(id: string): Promise<ScenarioResult> {
  return checked<ScenarioResult>(
    await fetch(`/api/demo/scenarios/${id}/run`, { method: "POST" }),
  );
}

export async function getLedger(
  trustZone: string,
  protectedEntityId = "project-aurora",
): Promise<LedgerClaim[]> {
  const query = new URLSearchParams({
    trust_zone_id: trustZone,
    protected_entity_id: protectedEntityId,
  });
  return checked<LedgerClaim[]>(await fetch(`/api/ledger?${query}`));
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

export async function getPolicy(): Promise<Policy> {
  return checked<Policy>(await fetch("/api/policy"));
}

export async function updatePolicy(policy: Policy): Promise<Policy> {
  return checked<Policy>(
    await fetch("/api/policy", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(policy),
    }),
  );
}

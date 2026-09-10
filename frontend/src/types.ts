export type ViewName =
  | "Chat"
  | "Privacy Pipeline"
  | "Collaboration"
  | "Privacy Dashboard"
  | "Exposure Ledger"
  | "Admin / Policy";

export type DemoMode = "trustsplit" | "cloud_only" | "local_only" | "basic_redaction";

export interface WorkflowEvent {
  sequence: number;
  state: string;
  actor: string;
  safe_summary: string;
}

export interface BrokerDecision {
  decision: string;
  reason_code: string;
  reason: string;
  released_text: string | null;
  released_precision: string | null;
  risk_before: number;
  risk_after: number;
  disclosure_delta: number;
  budget_cost: number;
}

export interface WorkflowResult {
  final_answer: string;
  outbound_payload: {
    provider_name: string;
    trust_zone_id: string;
    disclosures: Array<{
      text: string;
      category: string;
      precision: string;
      fact_keys: string[];
    }>;
  } | null;
  broker_decision: BrokerDecision;
  events: WorkflowEvent[];
  mode?: DemoMode;
  exposure_summary?: string;
}

export interface ScenarioResult {
  id: string;
  name: string;
  description: string;
  outcome: string;
  steps: Array<{ employee: string; decision: string; released: string; risk_after: number }>;
}

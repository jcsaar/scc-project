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
  outbound_payloads?: Array<{
    provider_name: string;
    trust_zone_id: string;
    disclosures: Array<{
      text: string;
      category: string;
      precision: string;
      fact_keys: string[];
    }>;
  }>;
  egress_evidence?: Array<{
    stage: string;
    decision: BrokerDecision;
    payload: WorkflowResult["outbound_payload"];
  }>;
  broker_decision: BrokerDecision;
  events: WorkflowEvent[];
  mode?: DemoMode;
  exposure_summary?: string;
  session_budget_remaining?: number | null;
  final_risk?: number;
  verification_status?: string;
}

export interface LedgerClaim {
  trust_zone_id: string;
  protected_entity_id: string;
  dimension: string;
  semantic_key: string;
  category: string;
  safe_representation: string;
  precision: string;
  base_weight: number;
}

export interface TrustZonePolicy {
  classification: string;
  disclosure_budget: number;
  retention_days: number | null;
  generalise_at: number;
  deny_at: number;
}

export interface Policy {
  max_clarification_rounds: number;
  hard_block_categories: string[];
  trust_zones: Record<string, TrustZonePolicy>;
}

export interface ScenarioResult {
  id: string;
  name: string;
  description: string;
  outcome: string;
  protected_entity_id: string;
  trust_zone_id: string;
  steps: Array<{ employee: string; decision: string; released: string; risk_after: number }>;
}

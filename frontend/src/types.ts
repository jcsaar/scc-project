export type DemoMode = "trustsplit" | "cloud_only" | "local_only" | "basic_redaction";

export interface WorkflowEvent {
  sequence: number;
  state: string;
  actor: string;
  safe_summary: string;
}

export type ProgressStage =
  | "local_read"
  | "sensitive_scan"
  | "safe_reconstruction"
  | "privacy_border"
  | "cloud_send"
  | "cloud_reasoning"
  | "local_verify"
  | "return_response";

export interface ProgressEvent {
  sequence: number;
  stage: ProgressStage;
  public_label: string;
  safe_summary: string;
  delay_ms: number;
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

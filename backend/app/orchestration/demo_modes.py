from app.domain.disclosures import BrokerDecision, DecisionKind, PrecisionLevel
from app.domain.workflow import WorkflowEvent, WorkflowState
from app.orchestration.state_machine import (
    CloudPayloadEvidence,
    DisclosureEvidence,
    TrustSplitWorkflow,
    WorkflowResult,
)


class DemoModeRunner:
    """Runs labelled, synthetic comparison modes without contacting a real provider."""

    _synthetic_exact = "Project Aurora serves Customer Northstar on Oracle RAC at 18,274 TPS."
    _redacted = "Project [REDACTED] serves Customer [REDACTED] on [REDACTED] at 18,274 TPS."

    def __init__(self, trustsplit: TrustSplitWorkflow) -> None:
        self._trustsplit = trustsplit

    async def run(
        self,
        mode: str,
        prompt: str,
        project_id: str,
        trust_zone_id: str,
        session_id: str | None = None,
    ) -> WorkflowResult:
        if mode == "trustsplit":
            result = await self._trustsplit.run(
                prompt, project_id, trust_zone_id, session_id=session_id
            )
            return result.model_copy(
                update={
                    "mode": mode,
                    "exposure_summary": (
                        "Bounded facts only; identifiers and exact values withheld."
                    ),
                }
            )
        if mode == "local_only":
            return self._local_only()
        if mode == "cloud_only":
            return self._simulated_cloud(mode, trust_zone_id, self._synthetic_exact)
        if mode == "basic_redaction":
            return self._simulated_cloud(mode, trust_zone_id, self._redacted)
        raise ValueError("Unsupported demo mode")

    @staticmethod
    def _events(summary: str, includes_cloud: bool) -> tuple[WorkflowEvent, ...]:
        events = [
            WorkflowEvent(
                sequence=1,
                state=WorkflowState.RECEIVE_PROMPT,
                actor="employee",
                safe_summary="Synthetic comparison prompt received.",
            )
        ]
        if includes_cloud:
            events.append(
                WorkflowEvent(
                    sequence=2,
                    state=WorkflowState.CLOUD_REASONING,
                    actor="cloud_ai",
                    safe_summary=summary,
                )
            )
        events.append(
            WorkflowEvent(
                sequence=len(events) + 1,
                state=WorkflowState.FINAL,
                actor="local_ai" if not includes_cloud else "cloud_ai",
                safe_summary="Deterministic comparison result ready.",
            )
        )
        return tuple(events)

    def _local_only(self) -> WorkflowResult:
        return WorkflowResult(
            mode="local_only",
            final_answer=(
                "Local analysis completed without external reasoning; utility is intentionally "
                "limited for comparison."
            ),
            outbound_payload=None,
            broker_decision=BrokerDecision(
                id="demo-local-only",
                decision=DecisionKind.LOCAL_ONLY,
                reason_code="comparison.local_only",
                reason="No cloud-bound message was created.",
                risk_before=0,
                risk_after=0,
                disclosure_delta=0,
                budget_cost=0,
            ),
            events=self._events("No cloud disclosure.", includes_cloud=False),
            exposure_summary="Zero external exposure; reduced cloud reasoning utility.",
        )

    def _simulated_cloud(
        self, mode: str, trust_zone_id: str, disclosed_text: str
    ) -> WorkflowResult:
        cloud_only = mode == "cloud_only"
        risk = 100 if cloud_only else 78
        decision = DecisionKind.ALLOW if cloud_only else DecisionKind.GENERALISE
        return WorkflowResult(
            mode=mode,
            final_answer=(
                "Simulated cloud recommendation generated from the intentionally exposed "
                "synthetic comparison payload."
            ),
            outbound_payload=CloudPayloadEvidence(
                provider_name="simulated_demo_cloud",
                trust_zone_id=trust_zone_id,
                disclosures=(
                    DisclosureEvidence(
                        text=disclosed_text,
                        category="comparison.synthetic",
                        precision=(
                            PrecisionLevel.EXACT if cloud_only else PrecisionLevel.APPROXIMATE
                        ),
                        fact_keys=("comparison.synthetic_payload",),
                    ),
                ),
            ),
            broker_decision=BrokerDecision(
                id=f"demo-{mode}",
                decision=decision,
                reason_code=f"comparison.{mode}",
                reason=(
                    "Intentional unsafe baseline: no privacy broker was used."
                    if cloud_only
                    else "Naive string redaction left identifying numeric structure exposed."
                ),
                released_text=disclosed_text,
                released_precision=(
                    PrecisionLevel.EXACT if cloud_only else PrecisionLevel.APPROXIMATE
                ),
                risk_before=0,
                risk_after=risk,
                disclosure_delta=risk,
                budget_cost=0,
            ),
            events=self._events(
                "Synthetic baseline payload exposed to the simulated cloud.",
                includes_cloud=True,
            ),
            exposure_summary=(
                "Full synthetic prompt exposed; comparison mode is intentionally unsafe."
                if cloud_only
                else "Names removed, but exact numeric and relational clues remain."
            ),
        )

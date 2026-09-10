import pytest
from pydantic import ValidationError

from app.domain.disclosures import (
    ApprovedDisclosure,
    BrokerDecision,
    DecisionKind,
    DisclosureProposal,
    PrecisionLevel,
)
from app.domain.providers import ApprovedCloudPayload, CloudContextRequest
from app.domain.workflow import WorkflowEvent, WorkflowState


def test_cloud_payload_rejects_private_fields() -> None:
    approved = ApprovedDisclosure(
        decision_id="decision-1",
        text="A regulated organisation handles 15k-20k TPS.",
        category="operations.throughput",
        precision=PrecisionLevel.BOUNDED_RANGE,
        fact_keys=("peak_tps",),
    )

    with pytest.raises(ValidationError, match="private_context"):
        ApprovedCloudPayload.model_validate(
            {
                "provider_name": "mock",
                "trust_zone_id": "company_cloud",
                "disclosures": [approved.model_dump()],
                "private_context": {"customer": "Northstar Financial Group"},
            }
        )


def test_cloud_payload_requires_approved_disclosures() -> None:
    proposal = DisclosureProposal(
        text="A regulated organisation handles 15k-20k TPS.",
        purpose="Recommend contention controls",
        category="operations.throughput",
        requested_precision=PrecisionLevel.BOUNDED_RANGE,
        protected_entity_ids=("project-aurora",),
        fact_keys=("peak_tps",),
    )

    with pytest.raises(ValidationError):
        ApprovedCloudPayload(
            provider_name="mock",
            trust_zone_id="company_cloud",
            disclosures=(proposal,),
        )


def test_broker_decision_records_risk_and_budget_evidence() -> None:
    decision = BrokerDecision(
        id="decision-1",
        decision=DecisionKind.GENERALISE,
        reason_code="precision_reduced",
        reason="Exact throughput is unnecessary.",
        released_text="15k-20k TPS",
        released_precision=PrecisionLevel.BOUNDED_RANGE,
        risk_before=41,
        risk_after=46,
        disclosure_delta=5,
        budget_cost=4,
    )

    assert decision.risk_after - decision.risk_before == decision.disclosure_delta


def test_cloud_context_request_and_workflow_event_forbid_extra_fields() -> None:
    request = CloudContextRequest(
        question="Does a natural partitioning key exist?",
        purpose="Evaluate sharding architecture",
        category="architecture.partitioning",
        requested_precision=PrecisionLevel.BOOLEAN,
    )

    event = WorkflowEvent(
        sequence=1,
        state=WorkflowState.CLOUD_REQUEST_CONTEXT,
        actor="cloud",
        safe_summary=request.question,
    )

    assert event.state is WorkflowState.CLOUD_REQUEST_CONTEXT
    with pytest.raises(ValidationError, match="raw_private_value"):
        WorkflowEvent.model_validate(
            {**event.model_dump(), "raw_private_value": "CustomerAccountID"}
        )

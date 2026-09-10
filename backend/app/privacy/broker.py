from uuid import uuid4

from pydantic import Field

from app.domain.disclosures import (
    ApprovedDisclosure,
    BrokerDecision,
    DecisionKind,
    DisclosureProposal,
    StrictFrozenModel,
)


class BrokerEvaluation(StrictFrozenModel):
    decision: BrokerDecision
    approved_disclosures: tuple[ApprovedDisclosure, ...] = Field(min_length=1)


class PrivacyBroker:
    def evaluate(self, proposal: DisclosureProposal) -> BrokerEvaluation:
        decision_id = str(uuid4())
        decision = BrokerDecision(
            id=decision_id,
            decision=DecisionKind.ALLOW,
            reason_code="minimum_safe_task",
            reason="The proposed task contains only the minimum useful abstract context.",
            released_text=proposal.text,
            released_precision=proposal.requested_precision,
            risk_before=0,
            risk_after=0,
            disclosure_delta=0,
            budget_cost=0,
        )
        disclosure = ApprovedDisclosure(
            decision_id=decision_id,
            text=proposal.text,
            category=proposal.category,
            precision=proposal.requested_precision,
            fact_keys=proposal.fact_keys,
        )
        return BrokerEvaluation(decision=decision, approved_disclosures=(disclosure,))

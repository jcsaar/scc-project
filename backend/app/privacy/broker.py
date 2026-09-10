from uuid import uuid4

from app.domain.disclosures import (
    ApprovedDisclosure,
    BrokerDecision,
    DecisionKind,
    DisclosureProposal,
    StrictFrozenModel,
)
from app.privacy.hard_rules import DisclosureInspection, HardRuleEngine


class BrokerEvaluation(StrictFrozenModel):
    decision: BrokerDecision
    approved_disclosures: tuple[ApprovedDisclosure, ...] = ()


class PrivacyBroker:
    def __init__(self, hard_rules: HardRuleEngine | None = None) -> None:
        self._hard_rules = hard_rules or HardRuleEngine()

    def evaluate(self, proposal: DisclosureProposal) -> BrokerEvaluation:
        decision_id = str(uuid4())
        hard_rule = self._hard_rules.inspect(
            DisclosureInspection(
                text=proposal.text,
                category=proposal.category,
                precision=proposal.requested_precision,
            )
        )
        if hard_rule.blocked:
            return BrokerEvaluation(
                decision=BrokerDecision(
                    id=decision_id,
                    decision=DecisionKind.DENY,
                    reason_code=hard_rule.reason_code,
                    reason=hard_rule.safe_reason,
                    risk_before=0,
                    risk_after=0,
                    disclosure_delta=0,
                    budget_cost=0,
                )
            )
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

from dataclasses import dataclass
from hashlib import sha256
from uuid import uuid4

from app.domain.disclosures import (
    ApprovedDisclosure,
    BrokerDecision,
    DecisionKind,
    DisclosureProposal,
    StrictFrozenModel,
)
from app.domain.policies import Policy
from app.ledger.repository import ExposureCommit, ExposureRepository
from app.privacy.budget import BudgetPolicy
from app.privacy.hard_rules import DisclosureInspection, HardRuleEngine
from app.privacy.risk import RiskClaim, RiskEngine


@dataclass(frozen=True)
class BrokerContext:
    session_id: str
    trust_zone_id: str
    dimension: str
    base_weight: int


class BrokerEvaluation(StrictFrozenModel):
    decision: BrokerDecision
    approved_disclosures: tuple[ApprovedDisclosure, ...] = ()


class PrivacyBroker:
    def __init__(
        self,
        hard_rules: HardRuleEngine | None = None,
        exposure_repository: ExposureRepository | None = None,
        policy: Policy | None = None,
        risk_engine: RiskEngine | None = None,
        budget_policy: BudgetPolicy | None = None,
    ) -> None:
        self._hard_rules = hard_rules or HardRuleEngine()
        self._exposure_repository = exposure_repository
        self._policy = policy
        self._risk_engine = risk_engine or RiskEngine()
        self._budget_policy = budget_policy or BudgetPolicy()

    def evaluate(
        self, proposal: DisclosureProposal, context: BrokerContext | None = None
    ) -> BrokerEvaluation:
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

        risk_before = 0
        risk_after = 0
        disclosure_delta = 0
        budget_cost = 0
        if context is not None:
            if self._exposure_repository is None or self._policy is None:
                raise RuntimeError("Broker context requires an exposure repository and policy")
            stored = self._exposure_repository.current_claims(
                context.trust_zone_id, proposal.protected_entity_ids[0]
            )
            existing = tuple(
                RiskClaim(
                    semantic_key=claim.semantic_key,
                    dimension=claim.dimension,
                    base_weight=claim.base_weight,
                    precision=claim.precision,
                )
                for claim in stored
            )
            candidate = RiskClaim(
                semantic_key=proposal.fact_keys[0],
                dimension=context.dimension,
                base_weight=context.base_weight,
                precision=proposal.requested_precision,
            )
            risk = self._risk_engine.delta(existing, candidate)
            risk_before = risk.risk_before
            risk_after = risk.risk_after
            disclosure_delta = risk.delta
            zone = self._policy.trust_zones[context.trust_zone_id]
            if risk_after >= zone.deny_at:
                return BrokerEvaluation(
                    decision=BrokerDecision(
                        id=decision_id,
                        decision=DecisionKind.DENY,
                        reason_code="risk.critical",
                        reason=(
                            "Cumulative disclosure would materially increase reconstruction risk."
                        ),
                        risk_before=risk_before,
                        risk_after=risk_after,
                        disclosure_delta=disclosure_delta,
                        budget_cost=0,
                    )
                )
            budget_cost = self._budget_policy.cost(proposal.requested_precision, disclosure_delta)
        decision = BrokerDecision(
            id=decision_id,
            decision=DecisionKind.ALLOW,
            reason_code="minimum_safe_task",
            reason="The proposed task contains only the minimum useful abstract context.",
            released_text=proposal.text,
            released_precision=proposal.requested_precision,
            risk_before=risk_before,
            risk_after=risk_after,
            disclosure_delta=disclosure_delta,
            budget_cost=budget_cost,
        )
        disclosure = ApprovedDisclosure(
            decision_id=decision_id,
            text=proposal.text,
            category=proposal.category,
            precision=proposal.requested_precision,
            fact_keys=proposal.fact_keys,
        )
        evaluation = BrokerEvaluation(decision=decision, approved_disclosures=(disclosure,))
        if context is not None and self._exposure_repository is not None:
            self._exposure_repository.commit_disclosure(
                ExposureCommit(
                    session_id=context.session_id,
                    protected_entity_id=proposal.protected_entity_ids[0],
                    dimension=context.dimension,
                    semantic_key=proposal.fact_keys[0],
                    category=proposal.category,
                    safe_representation=proposal.text,
                    representation_hash=sha256(proposal.text.encode()).hexdigest(),
                    precision=proposal.requested_precision.value,
                    base_weight=context.base_weight,
                    risk_before=risk_before,
                    risk_after=risk_after,
                    disclosure_delta=disclosure_delta,
                    budget_cost=budget_cost,
                    decision=decision.decision.value,
                    reason_code=decision.reason_code,
                )
            )
        return evaluation

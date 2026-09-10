from dataclasses import dataclass
from hashlib import sha256
from threading import RLock
from uuid import uuid4

from app.domain.disclosures import (
    ApprovedDisclosure,
    BrokerDecision,
    DecisionKind,
    DisclosureProposal,
    PrecisionLevel,
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
    _precision_order = (
        PrecisionLevel.BOOLEAN,
        PrecisionLevel.BROAD_CATEGORY,
        PrecisionLevel.COARSE_RANGE,
        PrecisionLevel.BOUNDED_RANGE,
        PrecisionLevel.APPROXIMATE,
        PrecisionLevel.EXACT,
    )

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
        self._decision_lock = RLock()

    def evaluate(
        self, proposal: DisclosureProposal, context: BrokerContext | None = None
    ) -> BrokerEvaluation:
        with self._decision_lock:
            return self._evaluate_locked(proposal, context)

    def update_policy(self, policy: Policy) -> None:
        with self._decision_lock:
            self._policy = policy

    def _evaluate_locked(
        self, proposal: DisclosureProposal, context: BrokerContext | None
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
        released_precision = proposal.requested_precision
        decision_kind = DecisionKind.ALLOW
        reason_code = "minimum_safe_task"
        reason = "The proposed task contains only the minimum useful abstract context."
        existing: tuple[RiskClaim, ...] = ()
        candidates: tuple[RiskClaim, ...] = ()
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
            risk_before = self._risk_engine.score(existing).scores.get(context.dimension, 0)
            candidates = self._candidates(proposal, context, released_precision)
            risk_after = self._risk_engine.score((*existing, *candidates)).scores.get(
                context.dimension, 0
            )
            disclosure_delta = max(0, risk_after - risk_before)
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
            if risk_after >= zone.generalise_at:
                requested_index = self._precision_order.index(proposal.requested_precision)
                for precision in reversed(self._precision_order[:requested_index]):
                    lowered = self._candidates(proposal, context, precision)
                    lowered_after = self._risk_engine.score((*existing, *lowered)).scores.get(
                        context.dimension, 0
                    )
                    if lowered_after < zone.generalise_at:
                        released_precision = precision
                        candidates = lowered
                        risk_after = lowered_after
                        disclosure_delta = max(0, risk_after - risk_before)
                        decision_kind = DecisionKind.GENERALISE
                        reason_code = "risk.generalised"
                        reason = "Cumulative exposure required a lower-precision representation."
                        break
                else:
                    return BrokerEvaluation(
                        decision=BrokerDecision(
                            id=decision_id,
                            decision=DecisionKind.DENY,
                            reason_code="risk.no_useful_precision",
                            reason="No useful precision fits the cumulative exposure policy.",
                            risk_before=risk_before,
                            risk_after=risk_after,
                            disclosure_delta=disclosure_delta,
                            budget_cost=0,
                        )
                    )
            budget_cost = self._budget_policy.cost(released_precision, disclosure_delta)
        decision = BrokerDecision(
            id=decision_id,
            decision=decision_kind,
            reason_code=reason_code,
            reason=reason,
            released_text=proposal.text,
            released_precision=released_precision,
            risk_before=risk_before,
            risk_after=risk_after,
            disclosure_delta=disclosure_delta,
            budget_cost=budget_cost,
        )
        disclosure = ApprovedDisclosure(
            decision_id=decision_id,
            text=proposal.text,
            category=proposal.category,
            precision=released_precision,
            fact_keys=proposal.fact_keys,
        )
        evaluation = BrokerEvaluation(decision=decision, approved_disclosures=(disclosure,))
        if context is not None and self._exposure_repository is not None:
            running_claims = list(existing)
            for index, candidate in enumerate(candidates):
                incremental = self._risk_engine.delta(tuple(running_claims), candidate)
                self._exposure_repository.commit_disclosure(
                    ExposureCommit(
                        session_id=context.session_id,
                        protected_entity_id=proposal.protected_entity_ids[0],
                        dimension=context.dimension,
                        semantic_key=candidate.semantic_key,
                        category=proposal.category,
                        safe_representation=proposal.text,
                        representation_hash=sha256(
                            f"{candidate.semantic_key}:{proposal.text}".encode()
                        ).hexdigest(),
                        precision=released_precision.value,
                        base_weight=context.base_weight,
                        risk_before=incremental.risk_before,
                        risk_after=incremental.risk_after,
                        disclosure_delta=incremental.delta,
                        budget_cost=budget_cost if index == 0 else 0,
                        decision=decision.decision.value,
                        reason_code=decision.reason_code,
                    )
                )
                running_claims.append(candidate)
        return evaluation

    @staticmethod
    def _candidates(
        proposal: DisclosureProposal,
        context: BrokerContext,
        precision: PrecisionLevel,
    ) -> tuple[RiskClaim, ...]:
        return tuple(
            RiskClaim(
                semantic_key=semantic_key,
                dimension=context.dimension,
                base_weight=context.base_weight,
                precision=precision,
            )
            for semantic_key in proposal.fact_keys
        )

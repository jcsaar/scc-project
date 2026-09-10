from collections import defaultdict

from pydantic import Field

from app.domain.disclosures import PrecisionLevel, StrictFrozenModel


class RiskClaim(StrictFrozenModel):
    semantic_key: str
    dimension: str
    base_weight: int = Field(ge=0, le=100)
    precision: PrecisionLevel


class SynergyRule(StrictFrozenModel):
    dimension: str
    required_keys: frozenset[str]
    bonus: int = Field(ge=0, le=100)


class RiskProfile(StrictFrozenModel):
    scores: dict[str, int]


class DisclosureRisk(StrictFrozenModel):
    dimension: str
    risk_before: int
    risk_after: int
    delta: int


class RiskEngine:
    _multipliers = {
        PrecisionLevel.BOOLEAN: 0.15,
        PrecisionLevel.BROAD_CATEGORY: 0.25,
        PrecisionLevel.COARSE_RANGE: 0.40,
        PrecisionLevel.BOUNDED_RANGE: 0.60,
        PrecisionLevel.APPROXIMATE: 0.80,
        PrecisionLevel.EXACT: 1.00,
    }

    def __init__(self, synergy_rules: tuple[SynergyRule, ...] = ()) -> None:
        self._synergy_rules = synergy_rules

    def score(self, claims: tuple[RiskClaim, ...]) -> RiskProfile:
        points: dict[tuple[str, str], int] = {}
        keys: dict[str, set[str]] = defaultdict(set)
        for claim in claims:
            contribution = round(claim.base_weight * self._multipliers[claim.precision])
            lookup = (claim.dimension, claim.semantic_key)
            points[lookup] = max(points.get(lookup, 0), contribution)
            keys[claim.dimension].add(claim.semantic_key)

        scores: dict[str, int] = defaultdict(int)
        for (dimension, _), contribution in points.items():
            scores[dimension] += contribution
        for rule in self._synergy_rules:
            if rule.required_keys.issubset(keys[rule.dimension]):
                scores[rule.dimension] += rule.bonus
        return RiskProfile(scores={key: min(100, value) for key, value in scores.items()})

    def delta(self, existing: tuple[RiskClaim, ...], candidate: RiskClaim) -> DisclosureRisk:
        before = self.score(existing).scores.get(candidate.dimension, 0)
        after = self.score((*existing, candidate)).scores.get(candidate.dimension, 0)
        return DisclosureRisk(
            dimension=candidate.dimension,
            risk_before=before,
            risk_after=after,
            delta=max(0, after - before),
        )

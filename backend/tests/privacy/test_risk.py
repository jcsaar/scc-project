from app.domain.disclosures import PrecisionLevel
from app.privacy.risk import RiskClaim, RiskEngine, SynergyRule


def claim(key: str, precision: PrecisionLevel, weight: int = 20) -> RiskClaim:
    return RiskClaim(
        semantic_key=key,
        dimension="customer_identity",
        base_weight=weight,
        precision=precision,
    )


def test_duplicate_and_less_precise_claims_add_zero_delta() -> None:
    engine = RiskEngine()
    existing = (claim("country", PrecisionLevel.BOUNDED_RANGE),)

    assert engine.delta(existing, claim("country", PrecisionLevel.BOUNDED_RANGE)).delta == 0
    assert engine.delta(existing, claim("country", PrecisionLevel.BROAD_CATEGORY)).delta == 0


def test_precision_upgrade_adds_only_incremental_risk() -> None:
    engine = RiskEngine()
    existing = (claim("throughput", PrecisionLevel.BROAD_CATEGORY, 40),)

    result = engine.delta(existing, claim("throughput", PrecisionLevel.EXACT, 40))

    assert result.risk_before == 10
    assert result.risk_after == 40
    assert result.delta == 30


def test_identifying_combination_activates_synergy_once() -> None:
    engine = RiskEngine(
        synergy_rules=(
            SynergyRule(
                dimension="customer_identity",
                required_keys=frozenset({"country", "industry", "company_size"}),
                bonus=12,
            ),
        )
    )
    existing = (
        claim("country", PrecisionLevel.BROAD_CATEGORY),
        claim("industry", PrecisionLevel.BROAD_CATEGORY),
    )

    result = engine.delta(existing, claim("company_size", PrecisionLevel.BROAD_CATEGORY))

    assert result.delta == 17
    assert (
        engine.delta(
            (*existing, claim("company_size", PrecisionLevel.BROAD_CATEGORY)),
            claim("company_size", PrecisionLevel.BROAD_CATEGORY),
        ).delta
        == 0
    )


def test_risk_is_capped_and_kept_separate_by_dimension() -> None:
    engine = RiskEngine()
    claims = tuple(claim(f"identity-{index}", PrecisionLevel.EXACT, 30) for index in range(4)) + (
        RiskClaim(
            semantic_key="database",
            dimension="architecture",
            base_weight=20,
            precision=PrecisionLevel.EXACT,
        ),
    )

    profile = engine.score(claims)

    assert profile.scores == {"customer_identity": 100, "architecture": 20}

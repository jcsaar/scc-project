from pathlib import Path

from app.domain.disclosures import DecisionKind, DisclosureProposal, PrecisionLevel
from app.domain.policies import PolicyLoader
from app.ledger.repository import ExposureRepository
from app.privacy.broker import BrokerContext, PrivacyBroker

POLICY = Path(__file__).parents[3] / "policy" / "default.yaml"


def test_generalise_threshold_reduces_released_precision() -> None:
    repository = ExposureRepository("sqlite://")
    repository.initialize()
    repository.register_session("session-1", "alice", "personal_cloud", 60)
    broker = PrivacyBroker(
        exposure_repository=repository,
        policy=PolicyLoader.load(POLICY),
    )
    proposal = DisclosureProposal(
        text="Mid-sized regulated organisation",
        purpose="Synthetic mosaic test",
        category="identity.company_size",
        requested_precision=PrecisionLevel.EXACT,
        protected_entity_ids=("project-aurora",),
        fact_keys=("company_size",),
    )

    result = broker.evaluate(
        proposal,
        BrokerContext("session-1", "personal_cloud", "customer_identity", 60),
    )

    assert result.decision.decision is DecisionKind.GENERALISE
    assert result.decision.released_precision is not PrecisionLevel.EXACT
    assert result.decision.risk_after < 75

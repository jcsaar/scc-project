from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from app.domain.disclosures import (
    DecisionKind,
    DisclosureCandidate,
    DisclosureProposal,
    PrecisionLevel,
)
from app.domain.policies import PolicyLoader
from app.ledger.repository import ExposureRepository
from app.privacy.broker import BrokerContext, PrivacyBroker
from app.privacy.risk import RiskEngine, SynergyRule

POLICY = Path(__file__).parents[3] / "policy" / "default.yaml"


def proposal(key: str, category: str, precision: PrecisionLevel) -> DisclosureProposal:
    alternatives = (
        (
            DisclosureCandidate(
                text=f"Lower-precision representation of {key}",
                category=category,
                precision=PrecisionLevel.APPROXIMATE,
                fact_keys=(key,),
            ),
        )
        if precision is PrecisionLevel.EXACT
        else ()
    )
    return DisclosureProposal(
        text=f"Safe representation of {key}",
        purpose="Evaluate architecture",
        category=category,
        requested_precision=precision,
        protected_entity_ids=("project-aurora",),
        fact_keys=(key,),
        alternatives=alternatives,
    )


def test_cross_employee_disclosures_share_provider_exposure(tmp_path: Path) -> None:
    repository = ExposureRepository(f"sqlite:///{tmp_path / 'ledger.db'}")
    repository.initialize()
    for session_id, employee in (
        ("alice-session", "alice"),
        ("bob-session", "bob"),
        ("charlie-session", "charlie"),
        ("dana-session", "dana"),
    ):
        repository.register_session(session_id, employee, "personal_cloud", 60)
    engine = RiskEngine(
        synergy_rules=(
            SynergyRule(
                dimension="customer_identity",
                required_keys=frozenset({"country", "industry", "company_size"}),
                bonus=12,
            ),
        )
    )
    broker = PrivacyBroker(
        exposure_repository=repository,
        policy=PolicyLoader.load(POLICY),
        risk_engine=engine,
    )

    alice = broker.evaluate(
        proposal("country", "identity.geography", PrecisionLevel.BROAD_CATEGORY),
        BrokerContext("alice-session", "personal_cloud", "customer_identity", 20),
    )
    bob = broker.evaluate(
        proposal("industry", "identity.industry", PrecisionLevel.BROAD_CATEGORY),
        BrokerContext("bob-session", "personal_cloud", "customer_identity", 20),
    )
    charlie = broker.evaluate(
        proposal("company_size", "identity.company_size", PrecisionLevel.BROAD_CATEGORY),
        BrokerContext("charlie-session", "personal_cloud", "customer_identity", 20),
    )
    dana = broker.evaluate(
        proposal("local_bank_status", "identity.bank_classification", PrecisionLevel.EXACT),
        BrokerContext("dana-session", "personal_cloud", "customer_identity", 60),
    )

    assert alice.decision.risk_after == 5
    assert bob.decision.risk_before == 5
    assert charlie.decision.disclosure_delta == 17
    assert dana.decision.decision is DecisionKind.DENY
    assert dana.decision.reason_code == "risk.critical"
    assert repository.remaining_budget("dana-session") == 60


def test_different_provider_has_separate_ledger_and_new_budget(tmp_path: Path) -> None:
    repository = ExposureRepository(f"sqlite:///{tmp_path / 'ledger.db'}")
    repository.initialize()
    repository.register_session("personal-session", "alice", "personal_cloud", 60)
    repository.register_session("company-session", "alice", "company_cloud", 100)
    broker = PrivacyBroker(
        exposure_repository=repository,
        policy=PolicyLoader.load(POLICY),
        risk_engine=RiskEngine(),
    )
    item = proposal("country", "identity.geography", PrecisionLevel.BROAD_CATEGORY)

    broker.evaluate(
        item,
        BrokerContext("personal-session", "personal_cloud", "customer_identity", 20),
    )
    company = broker.evaluate(
        item,
        BrokerContext("company-session", "company_cloud", "customer_identity", 20),
    )

    assert company.decision.risk_before == 0
    assert repository.remaining_budget("company-session") == 98


def test_repeated_fact_has_zero_delta_and_does_not_duplicate_claim(tmp_path: Path) -> None:
    repository = ExposureRepository(f"sqlite:///{tmp_path / 'ledger.db'}")
    repository.initialize()
    repository.register_session("alice-session", "alice", "personal_cloud", 60)
    repository.register_session("bob-session", "bob", "personal_cloud", 60)
    broker = PrivacyBroker(
        exposure_repository=repository,
        policy=PolicyLoader.load(POLICY),
        risk_engine=RiskEngine(),
    )
    item = proposal("country", "identity.geography", PrecisionLevel.BROAD_CATEGORY)

    broker.evaluate(
        item,
        BrokerContext("alice-session", "personal_cloud", "customer_identity", 20),
    )
    repeated = broker.evaluate(
        item,
        BrokerContext("bob-session", "personal_cloud", "customer_identity", 20),
    )

    assert repeated.decision.disclosure_delta == 0
    assert repeated.decision.budget_cost == 0
    assert len(repository.current_claims("personal_cloud", "project-aurora")) == 1
    assert repository.remaining_budget("bob-session") == 60


def test_concurrent_disclosures_are_serialized_against_shared_exposure(
    tmp_path: Path,
) -> None:
    repository = ExposureRepository(f"sqlite:///{tmp_path / 'ledger.db'}")
    repository.initialize()
    repository.register_session("alice-session", "alice", "personal_cloud", 60)
    repository.register_session("bob-session", "bob", "personal_cloud", 60)
    broker = PrivacyBroker(
        exposure_repository=repository,
        policy=PolicyLoader.load(POLICY),
        risk_engine=RiskEngine(),
    )
    barrier = Barrier(2)

    def evaluate(session_id: str, fact_key: str):
        barrier.wait()
        return broker.evaluate(
            proposal(fact_key, "identity.profile", PrecisionLevel.EXACT),
            BrokerContext(session_id, "personal_cloud", "customer_identity", 60),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (
            pool.submit(evaluate, "alice-session", "country"),
            pool.submit(evaluate, "bob-session", "industry"),
        )
        evaluations = tuple(future.result() for future in futures)

    assert {item.decision.decision for item in evaluations} == {
        DecisionKind.GENERALISE,
        DecisionKind.DENY,
    }
    claims = repository.current_claims("personal_cloud", "project-aurora")
    assert len(claims) == 1
    assert claims[0].precision == PrecisionLevel.APPROXIMATE.value

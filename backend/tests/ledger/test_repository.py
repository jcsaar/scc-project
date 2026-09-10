from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from app.ledger.repository import ExposureCommit, ExposureRepository, LedgerIntegrityError


def repository(path: Path) -> ExposureRepository:
    repo = ExposureRepository(f"sqlite:///{path}")
    repo.initialize()
    return repo


def test_in_memory_repository_supports_fastapi_worker_threads() -> None:
    repo = ExposureRepository("sqlite://")
    repo.initialize()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            repo.register_session, "thread-session", "alice", "company_cloud", 100
        )

    future.result()
    assert repo.remaining_budget("thread-session") == 100


def test_exposure_persists_across_repository_instances(tmp_path: Path) -> None:
    database = tmp_path / "ledger.db"
    first = repository(database)
    first.register_session("session-1", "alice", "personal_openai", 60)
    first.commit_disclosure(
        ExposureCommit(
            session_id="session-1",
            protected_entity_id="project-aurora",
            dimension="customer_identity",
            semantic_key="country",
            category="identity.geography",
            safe_representation="Southeast Asia",
            representation_hash="hash-country",
            precision="broad_category",
            risk_before=0,
            risk_after=5,
            disclosure_delta=5,
            budget_cost=2,
            decision="allow",
            reason_code="minimum_safe",
        )
    )

    reopened = repository(database)
    claims = reopened.current_claims("personal_openai", "project-aurora")

    assert len(claims) == 1
    assert claims[0].semantic_key == "country"
    assert reopened.remaining_budget("session-1") == 58


def test_claims_are_scoped_by_trust_zone_and_entity(tmp_path: Path) -> None:
    repo = repository(tmp_path / "ledger.db")
    repo.register_session("session-1", "alice", "personal_openai", 60)
    repo.commit_disclosure(
        ExposureCommit(
            session_id="session-1",
            protected_entity_id="project-aurora",
            dimension="architecture",
            semantic_key="database_platform",
            category="architecture.database",
            safe_representation="Clustered relational database",
            representation_hash="hash-db",
            precision="broad_category",
            risk_before=0,
            risk_after=4,
            disclosure_delta=4,
            budget_cost=2,
            decision="allow",
            reason_code="minimum_safe",
        )
    )

    assert repo.current_claims("company_openai", "project-aurora") == ()
    assert repo.current_claims("personal_openai", "project-phoenix") == ()


def test_failed_commit_rolls_back_claim_event_and_budget(tmp_path: Path) -> None:
    repo = repository(tmp_path / "ledger.db")

    with pytest.raises(LedgerIntegrityError):
        repo.commit_disclosure(
            ExposureCommit(
                session_id="missing-session",
                protected_entity_id="project-aurora",
                dimension="architecture",
                semantic_key="database_platform",
                category="architecture.database",
                safe_representation="Clustered database",
                representation_hash="hash-db",
                precision="broad_category",
                risk_before=0,
                risk_after=4,
                disclosure_delta=4,
                budget_cost=2,
                decision="allow",
                reason_code="minimum_safe",
            )
        )

    assert repo.current_claims("personal_openai", "project-aurora") == ()

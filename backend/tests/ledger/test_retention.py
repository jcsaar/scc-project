from datetime import UTC, datetime, timedelta

from app.ledger.retention import TimedExposureClaim, active_claims_at


def test_unknown_retention_persists_and_finite_retention_expires() -> None:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    persistent = TimedExposureClaim(semantic_key="country", active_until=None)
    expired = TimedExposureClaim(semantic_key="throughput", active_until=now - timedelta(seconds=1))
    active = TimedExposureClaim(semantic_key="database", active_until=now + timedelta(days=1))
    audit_history = (persistent, expired, active)

    assert active_claims_at(audit_history, now) == (persistent, active)
    assert audit_history == (persistent, expired, active)

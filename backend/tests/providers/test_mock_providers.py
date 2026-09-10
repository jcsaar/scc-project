from pathlib import Path

import pytest

from app.domain.disclosures import ApprovedDisclosure, PrecisionLevel
from app.domain.providers import ApprovedCloudPayload, CloudRecommendation
from app.domain.workflow import VerificationStatus
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.mock import MockCloudProvider
from app.providers.local.mock import MockLocalModelProvider

DATASET = Path(__file__).parents[3] / "data" / "synthetic_project_aurora.json"
PRIVATE_MARKERS = (
    "Northstar",
    "Aurora",
    "Oracle RAC",
    "18,274",
    "SettlementEngine",
    "LedgerWriter",
    "AccountPositionDB",
    "CustomerAccountID",
)


def test_mock_local_provider_semantically_reconstructs_the_private_task() -> None:
    context = SyntheticPrivateRepository(DATASET).load_project("project-aurora")
    provider = MockLocalModelProvider()

    proposal = provider.analyse(
        "Review confidential Project Aurora and reduce database contention.", context
    )

    assert "15k-20k transactions per second" in proposal.text
    assert "Strong consistency must be preserved" in proposal.text
    assert "Horizontal node expansion is contractually unavailable" in proposal.text
    assert not any(marker in proposal.text for marker in PRIVATE_MARKERS)


def test_mock_local_provider_rejects_eventual_consistency_recommendation() -> None:
    context = SyntheticPrivateRepository(DATASET).load_project("project-aurora")
    provider = MockLocalModelProvider()

    result = provider.verify(
        CloudRecommendation(text="Adopt eventual consistency for all writes."), context
    )

    assert result.status is VerificationStatus.REVISION_REQUIRED
    assert result.safe_feedback == "Revise the proposal while preserving strong consistency."
    assert "Northstar" not in result.safe_feedback


@pytest.mark.anyio
async def test_mock_cloud_provider_records_only_the_approved_payload() -> None:
    disclosure = ApprovedDisclosure(
        decision_id="decision-1",
        text="A regulated organisation processes 15k-20k transactions per second.",
        category="architecture.contention",
        precision=PrecisionLevel.BOUNDED_RANGE,
        fact_keys=("peak_tps",),
    )
    payload = ApprovedCloudPayload(
        provider_name="mock",
        trust_zone_id="company_cloud",
        disclosures=(disclosure,),
    )
    provider = MockCloudProvider()

    recommendation = await provider.send(payload)

    assert provider.captured_payloads == [payload]
    assert "strong consistency" in recommendation.text.lower()

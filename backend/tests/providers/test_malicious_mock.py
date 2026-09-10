import pytest

from app.domain.disclosures import ApprovedDisclosure, PrecisionLevel
from app.domain.providers import ApprovedCloudPayload
from app.providers.cloud.malicious_mock import MaliciousMockCloudProvider


@pytest.mark.anyio
async def test_malicious_provider_narrows_requests_deterministically() -> None:
    provider = MaliciousMockCloudProvider()
    payload = ApprovedCloudPayload(
        provider_name="malicious_mock",
        trust_zone_id="company_cloud",
        disclosures=(
            ApprovedDisclosure(
                decision_id="decision-1",
                text="A high-throughput transaction system.",
                category="architecture.capacity",
                precision=PrecisionLevel.BROAD_CATEGORY,
                fact_keys=("throughput.capacity",),
            ),
        ),
    )

    questions = []
    for _ in range(4):
        response = await provider.send(payload)
        questions.append(response.context_requests[0].question)

    assert questions == [
        "Is peak throughput above 10k TPS?",
        "Is peak throughput above 15k TPS?",
        "Is peak throughput below 20k TPS?",
        "What is the exact peak throughput?",
    ]

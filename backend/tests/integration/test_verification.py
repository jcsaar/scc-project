from pathlib import Path

import httpx
import pytest

from app.domain.providers import ApprovedCloudPayload, CloudRecommendation
from app.domain.workflow import WorkflowState
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.base import CloudProvider
from app.providers.local.mock import MockLocalModelProvider

DATASET = Path(__file__).parents[3] / "data" / "synthetic_project_aurora.json"
PRIVATE_MARKERS = ("Northstar", "Oracle RAC", "18,274", "CustomerAccountID")


class RevisionCloud(CloudProvider):
    def __init__(self) -> None:
        self.payloads: list[ApprovedCloudPayload] = []

    @property
    def provider_name(self) -> str:
        return "revision-cloud"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        self.payloads.append(payload)
        if len(self.payloads) == 1:
            return CloudRecommendation(text="Use eventual consistency for all writes.")
        return CloudRecommendation(text="Partition writes while preserving strong consistency.")


class TimeoutCloud(CloudProvider):
    @property
    def provider_name(self) -> str:
        return "timeout-cloud"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        raise httpx.ReadTimeout("provider timed out")


def workflow(provider: CloudProvider) -> TrustSplitWorkflow:
    return TrustSplitWorkflow(
        SyntheticPrivateRepository(DATASET),
        MockLocalModelProvider(),
        PrivacyBroker(),
        provider,
    )


@pytest.mark.anyio
async def test_verifier_requests_safe_revision_for_consistency_violation() -> None:
    provider = RevisionCloud()

    result = await workflow(provider).run("Reduce contention", "project-aurora", "company_cloud")

    assert len(provider.payloads) == 2
    feedback = provider.payloads[1].disclosures[0].text
    assert feedback == "Revise the proposal while preserving strong consistency."
    assert not any(marker in feedback for marker in PRIVATE_MARKERS)
    assert WorkflowState.CLOUD_REVISION in [event.state for event in result.events]
    assert "strong consistency" in result.final_answer.lower()


@pytest.mark.anyio
async def test_provider_timeout_falls_back_to_local_synthesis() -> None:
    result = await workflow(TimeoutCloud()).run(
        "Reduce contention", "project-aurora", "company_cloud"
    )

    assert "local-only fallback" in result.final_answer.lower()
    assert WorkflowState.LOCAL_SYNTHESIS in [event.state for event in result.events]
    assert result.events[-1].state is WorkflowState.FINAL

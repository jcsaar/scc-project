from pathlib import Path

import pytest

from app.domain.disclosures import PrecisionLevel
from app.domain.providers import ApprovedCloudPayload, CloudContextRequest, CloudRecommendation
from app.domain.workflow import WorkflowState
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.base import CloudProvider
from app.providers.local.mock import MockLocalModelProvider

DATASET = Path(__file__).parents[3] / "data" / "synthetic_project_aurora.json"


class ScriptedCloudProvider(CloudProvider):
    def __init__(self, responses: list[CloudRecommendation]) -> None:
        self.responses = responses
        self.captured_payloads: list[ApprovedCloudPayload] = []

    @property
    def provider_name(self) -> str:
        return "scripted"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        self.captured_payloads.append(payload)
        return self.responses[min(len(self.captured_payloads) - 1, len(self.responses) - 1)]


def workflow(provider: CloudProvider, max_rounds: int = 4) -> TrustSplitWorkflow:
    return TrustSplitWorkflow(
        SyntheticPrivateRepository(DATASET),
        MockLocalModelProvider(),
        PrivacyBroker(),
        provider,
        max_clarification_rounds=max_rounds,
    )


@pytest.mark.anyio
async def test_partition_question_returns_boolean_through_two_broker_checks() -> None:
    request = CloudContextRequest(
        question="Does a natural partitioning key exist?",
        purpose="Evaluate sharding architecture",
        category="architecture.partitioning",
        requested_precision=PrecisionLevel.BOOLEAN,
    )
    provider = ScriptedCloudProvider(
        [
            CloudRecommendation(text="Need one fact.", context_requests=(request,)),
            CloudRecommendation(text="Partition writes while preserving strong consistency."),
        ]
    )

    result = await workflow(provider).run("Reduce contention", "project-aurora", "company_cloud")

    oracle_payload = provider.captured_payloads[1].disclosures[0].text
    assert oracle_payload == "Yes, a stable natural partitioning key exists."
    assert "CustomerAccountID" not in oracle_payload
    states = [event.state for event in result.events]
    assert WorkflowState.BROKER_VALIDATE_QUERY in states
    assert WorkflowState.BROKER_VALIDATE_RESPONSE in states
    assert WorkflowState.LOCAL_ORACLE in states


@pytest.mark.anyio
async def test_identity_request_is_denied_before_local_oracle() -> None:
    request = CloudContextRequest(
        question="What is the exact customer identity?",
        purpose="Narrow the organisation",
        category="identity.customer",
        requested_precision=PrecisionLevel.EXACT,
    )
    provider = ScriptedCloudProvider(
        [CloudRecommendation(text="Continue without it.", context_requests=(request,))]
    )

    result = await workflow(provider).run("Reduce contention", "project-aurora", "company_cloud")

    states = [event.state for event in result.events]
    assert WorkflowState.BROKER_VALIDATE_QUERY in states
    assert WorkflowState.LOCAL_ORACLE not in states
    assert len(provider.captured_payloads) == 1


@pytest.mark.anyio
async def test_repeated_context_requests_stop_at_round_limit() -> None:
    request = CloudContextRequest(
        question="Does a natural partitioning key exist?",
        purpose="Evaluate sharding architecture",
        category="architecture.partitioning",
        requested_precision=PrecisionLevel.BOOLEAN,
    )
    provider = ScriptedCloudProvider(
        [CloudRecommendation(text="Still asking.", context_requests=(request,))]
    )

    result = await workflow(provider, max_rounds=2).run(
        "Reduce contention", "project-aurora", "company_cloud"
    )

    assert len(provider.captured_payloads) == 3
    assert result.events[-1].state is WorkflowState.FINAL

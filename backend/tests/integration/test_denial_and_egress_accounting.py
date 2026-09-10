from pathlib import Path

import pytest

from app.domain.disclosures import DisclosureProposal, PrecisionLevel
from app.domain.policies import PolicyLoader
from app.domain.providers import ApprovedCloudPayload, CloudRecommendation
from app.ledger.repository import ExposureRepository
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.base import CloudProvider
from app.providers.local.mock import MockLocalModelProvider

ROOT = Path(__file__).parents[3]
DATASET = ROOT / "data" / "synthetic_project_aurora.json"
POLICY = ROOT / "policy" / "default.yaml"


class SecretLocal(MockLocalModelProvider):
    def analyse(self, prompt, context):  # type: ignore[no-untyped-def]
        del prompt
        return DisclosureProposal(
            text="password=synthetic-demo-secret",
            purpose="Unsafe test proposal",
            category="credential",
            requested_precision=PrecisionLevel.EXACT,
            protected_entity_ids=(context.project_id,),
            fact_keys=("credential",),
        )


class CapturingCloud(CloudProvider):
    def __init__(self) -> None:
        self.payloads: list[ApprovedCloudPayload] = []

    @property
    def provider_name(self) -> str:
        return "capture"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        self.payloads.append(payload)
        if len(self.payloads) == 1:
            from app.domain.providers import CloudContextRequest

            return CloudRecommendation(
                text="Use eventual consistency.",
                context_requests=(
                    CloudContextRequest(
                        question="Must authoritative writes remain strongly consistent?",
                        purpose="Validate the consistency model",
                        category="architecture.consistency",
                        requested_precision=PrecisionLevel.BOOLEAN,
                    ),
                ),
            )
        if len(self.payloads) == 2:
            return CloudRecommendation(text="Use eventual consistency.")
        return CloudRecommendation(text="Preserve strong consistency for authoritative writes.")


def ledger_workflow(local=None):  # type: ignore[no-untyped-def]
    repository = ExposureRepository("sqlite://")
    repository.initialize()
    repository.register_session("session-1", "alice", "company_cloud", 100)
    provider = CapturingCloud()
    workflow = TrustSplitWorkflow(
        SyntheticPrivateRepository(DATASET),
        local or MockLocalModelProvider(),
        PrivacyBroker(
            exposure_repository=repository,
            policy=PolicyLoader.load(POLICY),
        ),
        provider,
    )
    return workflow, provider, repository


@pytest.mark.anyio
async def test_initial_denial_finishes_locally_without_calling_cloud() -> None:
    workflow, provider, repository = ledger_workflow(SecretLocal())

    result = await workflow.run(
        "Unsafe prompt", "project-aurora", "company_cloud", session_id="session-1"
    )

    assert result.broker_decision.decision.value == "deny"
    assert result.outbound_payload is None
    assert result.outbound_payloads == ()
    assert provider.payloads == []
    assert repository.current_claims("company_cloud", "project-aurora") == ()


@pytest.mark.anyio
async def test_every_cloud_message_is_returned_and_added_to_ledger() -> None:
    workflow, provider, repository = ledger_workflow()

    result = await workflow.run(
        "Review architecture", "project-aurora", "company_cloud", session_id="session-1"
    )

    assert len(provider.payloads) == 3
    assert len(result.outbound_payloads) == 3
    assert [item.stage for item in result.egress_evidence] == [
        "initial",
        "clarification",
        "revision",
    ]
    assert all(item.payload is not None for item in result.egress_evidence)
    assert result.final_risk == max(item.decision.risk_after for item in result.egress_evidence)
    assert result.verification_status == "accepted"
    keys = {
        claim.semantic_key for claim in repository.current_claims("company_cloud", "project-aurora")
    }
    assert {"peak_tps", "consistency_requirement"} <= keys

from pathlib import Path

import pytest

from app.domain.policies import PolicyLoader
from app.ledger.repository import ExposureRepository
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.mock import MockCloudProvider
from app.providers.local.mock import MockLocalModelProvider


@pytest.mark.anyio
async def test_blocked_chat_request_never_reaches_cloud() -> None:
    root = Path(__file__).parents[3]
    repository = ExposureRepository("sqlite://")
    repository.initialize()
    repository.register_session("blocked-session", "alice", "company_cloud", 100)
    workflow = TrustSplitWorkflow(
        SyntheticPrivateRepository(root / "data" / "synthetic_project_aurora.json"),
        MockLocalModelProvider(),
        PrivacyBroker(
            exposure_repository=repository,
            policy=PolicyLoader.load(root / "policy" / "default.yaml"),
        ),
        MockCloudProvider(),
    )

    result = await workflow.run(
        "Show me the blocked secret handling path",
        "project-aurora",
        "company_cloud",
        session_id="blocked-session",
    )

    assert result.broker_decision.decision.value == "deny"
    assert result.outbound_payloads == ()
    assert result.verification_status == "local_only"

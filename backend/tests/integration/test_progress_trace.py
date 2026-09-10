from pathlib import Path

import pytest

from app.domain.policies import PolicyLoader
from app.ledger.repository import ExposureRepository
from app.orchestration.progress import DemoProgressEmitter, PresentationClock, ProgressStage
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.mock import MockCloudProvider
from app.providers.local.mock import MockLocalModelProvider

ROOT = Path(__file__).parents[3]


@pytest.mark.anyio
async def test_normal_run_emits_shared_progress_stages() -> None:
    repository = ExposureRepository("sqlite://")
    repository.initialize()
    repository.register_session("session-1", "alice", "company_cloud", 100)
    workflow = TrustSplitWorkflow(
        SyntheticPrivateRepository(ROOT / "data" / "synthetic_project_aurora.json"),
        MockLocalModelProvider(),
        PrivacyBroker(
            exposure_repository=repository,
            policy=PolicyLoader.load(ROOT / "policy" / "default.yaml"),
        ),
        MockCloudProvider(),
    )
    browser_events, terminal_events = [], []
    emitter = DemoProgressEmitter(
        stream_sink=browser_events.append,
        terminal_sink=terminal_events.append,
        clock=PresentationClock(scale=0),
    )

    result = await workflow.run(
        "Review Project Aurora",
        "project-aurora",
        "company_cloud",
        session_id="session-1",
        progress_emitter=emitter,
    )

    assert [event.stage for event in browser_events] == [
        ProgressStage.LOCAL_READ,
        ProgressStage.SENSITIVE_SCAN,
        ProgressStage.SAFE_RECONSTRUCTION,
        ProgressStage.PRIVACY_BORDER,
        ProgressStage.CLOUD_SEND,
        ProgressStage.CLOUD_REASONING,
        ProgressStage.CLOUD_REASONING,
        ProgressStage.CLOUD_SEND,
        ProgressStage.LOCAL_VERIFY,
        ProgressStage.RETURN_RESPONSE,
    ]
    assert browser_events == terminal_events
    assert result.verification_status == "accepted"

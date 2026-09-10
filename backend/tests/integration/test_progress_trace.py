from io import StringIO
from pathlib import Path

import pytest

from app.domain.policies import PolicyLoader
from app.ledger.repository import ExposureRepository
from app.orchestration.progress import DemoProgressEmitter, PresentationClock, ProgressStage
from app.orchestration.state_machine import TrustSplitWorkflow
from app.presentation.terminal import TerminalPresenter
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
    reconstruction = next(
        event for event in browser_events if event.stage is ProgressStage.SAFE_RECONSTRUCTION
    )
    assert reconstruction.safe_detail is not None
    assert "15k-20k" in reconstruction.safe_detail
    assert "Northstar" not in reconstruction.safe_detail
    assert "18,274" not in reconstruction.safe_detail


@pytest.mark.anyio
async def test_denied_prompt_exposes_only_a_sanitized_reconstruction_preview() -> None:
    repository = ExposureRepository("sqlite://")
    repository.initialize()
    repository.register_session("session-deny", "alice", "company_cloud", 100)
    workflow = TrustSplitWorkflow(
        SyntheticPrivateRepository(ROOT / "data" / "synthetic_project_aurora.json"),
        MockLocalModelProvider(),
        PrivacyBroker(
            exposure_repository=repository,
            policy=PolicyLoader.load(ROOT / "policy" / "default.yaml"),
        ),
        MockCloudProvider(),
    )
    browser_events = []
    terminal_output = StringIO()
    terminal = TerminalPresenter(stream=terminal_output, private_trace=True)
    emitter = DemoProgressEmitter(
        stream_sink=browser_events.append,
        terminal_sink=terminal,
        private_terminal_sink=terminal.private,
        clock=PresentationClock(scale=0),
    )

    result = await workflow.run(
        "Look up the exact customer identity for Aisha Rahman, NRIC S1234567A.",
        "project-aurora",
        "company_cloud",
        session_id="session-deny",
        progress_emitter=emitter,
    )

    reconstruction = next(
        event for event in browser_events if event.stage is ProgressStage.SAFE_RECONSTRUCTION
    )
    assert result.broker_decision.decision.value == "deny"
    assert reconstruction.safe_detail == (
        "Safe alternative prepared locally: explain a customer-lookup workflow without exposing "
        "identity fields. Exact identity lookup remains local."
    )
    assert "Aisha Rahman" not in reconstruction.safe_detail
    assert "S1234567A" not in reconstruction.safe_detail
    assert "Matched indicators: exact customer, NRIC" in terminal_output.getvalue()
    assert "Confidence: 100%" in terminal_output.getvalue()
    assert "Aisha Rahman" not in terminal_output.getvalue()
    assert "S1234567A" not in terminal_output.getvalue()

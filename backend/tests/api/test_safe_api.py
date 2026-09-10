import json
from pathlib import Path

import httpx
import pytest

from app.ledger.repository import ExposureCommit, ExposureRepository
from app.main import create_app

POLICY = Path(__file__).parents[3] / "policy" / "default.yaml"
DATASET = Path(__file__).parents[3] / "data" / "synthetic_project_aurora.json"
PRIVATE_MARKERS = ("Northstar", "Oracle RAC", "18,274", "CustomerAccountID")


@pytest.mark.anyio
async def test_session_status_and_sse_replay_are_safe() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/sessions",
            json={
                "employee_id": "alice",
                "mode": "trustsplit",
                "trust_zone_id": "company_cloud",
                "project_id": "project-aurora",
            },
        )
        session_id = created.json()["id"]
        result = await client.post(
            f"/api/sessions/{session_id}/run", json={"prompt": "Review Project Aurora"}
        )
        status = await client.get(f"/api/sessions/{session_id}")
        events = await client.get(f"/api/sessions/{session_id}/events?after_sequence=4")

    combined = result.text + status.text + events.text
    assert status.json()["status"] == "complete"
    assert events.headers["content-type"].startswith("text/event-stream")
    assert "id: 5" in events.text
    assert "id: 4\n" not in events.text
    assert not any(marker in combined for marker in PRIVATE_MARKERS)


@pytest.mark.anyio
async def test_policy_api_returns_and_validates_non_secret_configuration() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/policy")
        invalid = response.json()
        invalid["trust_zones"]["personal_cloud"]["deny_at"] = 10
        rejected = await client.put("/api/policy", json=invalid)

    assert response.status_code == 200
    assert response.json()["max_clarification_rounds"] == 4
    assert "api_key" not in response.text.lower()
    assert rejected.status_code == 422


@pytest.mark.anyio
async def test_policy_update_changes_subsequent_broker_decisions() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        policy = (await client.get("/api/policy")).json()
        policy["trust_zones"]["personal_cloud"]["generalise_at"] = 20
        updated = await client.put("/api/policy", json=policy)
        session = await client.post(
            "/api/sessions",
            json={
                "employee_id": "policy-auditor",
                "mode": "trustsplit",
                "trust_zone_id": "personal_cloud",
                "project_id": "project-aurora",
            },
        )
        result = await client.post(
            f"/api/sessions/{session.json()['id']}/run",
            json={"prompt": "Review synthetic Project Aurora"},
        )

    assert updated.status_code == 200
    assert result.json()["broker_decision"]["decision"] == "generalise"


@pytest.mark.anyio
async def test_policy_update_changes_clarification_limit_for_subsequent_runs() -> None:
    from app.domain.disclosures import PrecisionLevel
    from app.domain.policies import PolicyLoader
    from app.domain.providers import ApprovedCloudPayload, CloudContextRequest, CloudRecommendation
    from app.ledger.repository import ExposureRepository
    from app.orchestration.state_machine import TrustSplitWorkflow
    from app.privacy.broker import PrivacyBroker
    from app.private_data.repository import SyntheticPrivateRepository
    from app.providers.cloud.base import CloudProvider
    from app.providers.local.mock import MockLocalModelProvider

    class RepeatingContextCloud(CloudProvider):
        @property
        def provider_name(self) -> str:
            return "repeating-context"

        async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
            del payload
            return CloudRecommendation(
                text="Use eventual consistency.",
                context_requests=(
                    CloudContextRequest(
                        question="Must authoritative writes remain strongly consistent?",
                        purpose="Validate consistency",
                        category="architecture.consistency",
                        requested_precision=PrecisionLevel.BOOLEAN,
                    ),
                ),
            )

    repository = ExposureRepository("sqlite://")
    repository.initialize()
    workflow = TrustSplitWorkflow(
        SyntheticPrivateRepository(DATASET),
        MockLocalModelProvider(),
        PrivacyBroker(
            exposure_repository=repository,
            policy=PolicyLoader.load(POLICY),
        ),
        RepeatingContextCloud(),
    )
    transport = httpx.ASGITransport(
        app=create_app(workflow=workflow, exposure_repository=repository)
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        policy = (await client.get("/api/policy")).json()
        policy["max_clarification_rounds"] = 1
        updated = await client.put("/api/policy", json=policy)
        session = await client.post(
            "/api/sessions",
            json={
                "employee_id": "policy-auditor",
                "mode": "trustsplit",
                "trust_zone_id": "company_cloud",
                "project_id": "project-aurora",
            },
        )
        result = await client.post(
            f"/api/sessions/{session.json()['id']}/run",
            json={"prompt": "Review synthetic Project Aurora"},
        )

    assert updated.status_code == 200
    stages = [item["stage"] for item in result.json()["egress_evidence"]]
    assert stages.count("clarification") == 1


@pytest.mark.anyio
async def test_ledger_api_returns_only_safe_representations(tmp_path: Path) -> None:
    repository = ExposureRepository(f"sqlite:///{tmp_path / 'ledger.db'}")
    repository.initialize()
    repository.register_session("session-1", "alice", "personal_cloud", 60)
    repository.commit_disclosure(
        ExposureCommit(
            session_id="session-1",
            protected_entity_id="project-aurora",
            dimension="architecture",
            semantic_key="database_platform",
            category="architecture.database",
            safe_representation="Clustered relational database",
            representation_hash="safe-hash",
            precision="broad_category",
            risk_before=0,
            risk_after=5,
            disclosure_delta=5,
            budget_cost=2,
            decision="allow",
            reason_code="minimum_safe",
        )
    )
    transport = httpx.ASGITransport(app=create_app(exposure_repository=repository))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/ledger",
            params={"trust_zone_id": "personal_cloud", "protected_entity_id": "project-aurora"},
        )

    assert response.status_code == 200
    assert response.json()[0]["safe_representation"] == "Clustered relational database"
    assert not any(marker in json.dumps(response.json()) for marker in PRIVATE_MARKERS)

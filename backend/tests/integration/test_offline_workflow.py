import httpx
import pytest

from app.domain.workflow import WorkflowState
from app.main import create_app

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


@pytest.mark.anyio
async def test_offline_workflow_exposes_only_the_safe_cloud_payload() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        session_response = await client.post(
            "/api/sessions",
            json={
                "employee_id": "alice",
                "mode": "trustsplit",
                "trust_zone_id": "company_cloud",
                "project_id": "project-aurora",
            },
        )
        assert session_response.status_code == 201
        run_response = await client.post(
            f"/api/sessions/{session_response.json()['id']}/run",
            json={
                "prompt": (
                    "Review confidential Project Aurora and recommend how to reduce database "
                    "contention without violating licensing or consistency requirements."
                )
            },
        )

    assert run_response.status_code == 200
    result = run_response.json()
    cloud_text = result["outbound_payload"]["disclosures"][0]["text"]
    assert "15k-20k transactions per second" in cloud_text
    assert not any(marker in cloud_text for marker in PRIVATE_MARKERS)
    assert result["broker_decision"]["decision"] == "allow"
    assert "strong consistency" in result["final_answer"].lower()
    assert [event["state"] for event in result["events"]] == [
        WorkflowState.RECEIVE_PROMPT,
        WorkflowState.LOCAL_ANALYSIS,
        WorkflowState.CREATE_SAFE_TASK,
        WorkflowState.BROKER_VALIDATE_OUTBOUND,
        WorkflowState.CLOUD_REASONING,
        WorkflowState.CLOUD_REQUEST_CONTEXT,
        WorkflowState.BROKER_VALIDATE_QUERY,
        WorkflowState.LOCAL_ORACLE,
        WorkflowState.BROKER_VALIDATE_RESPONSE,
        WorkflowState.CLOUD_CONTINUE,
        WorkflowState.LOCAL_VERIFY,
        WorkflowState.FINAL,
    ]

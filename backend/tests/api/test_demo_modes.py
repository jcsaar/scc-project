import httpx
import pytest

from app.main import create_app


async def run_mode(client: httpx.AsyncClient, mode: str) -> dict[str, object]:
    created = await client.post(
        "/api/sessions",
        json={
            "employee_id": "alice",
            "mode": mode,
            "trust_zone_id": "company_cloud",
            "project_id": "project-aurora",
        },
    )
    assert created.status_code == 201
    response = await client.post(
        f"/api/sessions/{created.json()['id']}/run",
        json={"prompt": "Review the synthetic Project Aurora architecture."},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.anyio
async def test_comparison_modes_report_truthful_exposure() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        cloud_only = await run_mode(client, "cloud_only")
        local_only = await run_mode(client, "local_only")
        redaction = await run_mode(client, "basic_redaction")
        trustsplit = await run_mode(client, "trustsplit")

    assert "18,274" in str(cloud_only["outbound_payload"])
    assert cloud_only["broker_decision"]["risk_after"] == 100  # type: ignore[index]
    assert local_only["outbound_payload"] is None
    assert local_only["broker_decision"]["decision"] == "local_only"  # type: ignore[index]
    assert "18,274" in str(redaction["outbound_payload"])
    assert "Northstar" not in str(redaction["outbound_payload"])
    assert "18,274" not in str(trustsplit["outbound_payload"])
    assert "15k-20k transactions per second" in str(trustsplit["outbound_payload"])


@pytest.mark.anyio
async def test_repeatable_demo_scenarios_reach_expected_decisions() -> None:
    from app.ledger.repository import ExposureRepository

    repository = ExposureRepository("sqlite://")
    transport = httpx.ASGITransport(app=create_app(exposure_repository=repository))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        listing = await client.get("/api/demo/scenarios")
        mosaic = await client.post("/api/demo/scenarios/mosaic/run")
        malicious = await client.post("/api/demo/scenarios/malicious_cloud/run")

    assert {item["id"] for item in listing.json()} == {
        "legitimate",
        "mosaic",
        "malicious_cloud",
    }
    assert [step["decision"] for step in mosaic.json()["steps"]] == [
        "allow",
        "allow",
        "generalise",
        "deny",
    ]
    assert malicious.json()["steps"][-1]["decision"] == "deny"
    assert malicious.json()["steps"][-1]["risk_after"] >= 70
    assert repository.current_claims("personal_cloud", mosaic.json()["protected_entity_id"])

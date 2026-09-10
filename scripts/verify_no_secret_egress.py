#!/usr/bin/env python3
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import create_app  # noqa: E402

PRIVATE_MARKERS = (
    "Northstar",
    "Oracle RAC",
    "18,274",
    "SettlementEngine",
    "LedgerWriter",
    "AccountPositionDB",
    "CustomerAccountID",
)


async def run_mode(client: httpx.AsyncClient, mode: str) -> dict[str, object]:
    created = await client.post(
        "/api/sessions",
        json={
            "employee_id": "canary-auditor",
            "mode": mode,
            "trust_zone_id": "company_cloud",
            "project_id": "project-aurora",
        },
    )
    created.raise_for_status()
    result = await client.post(
        f"/api/sessions/{created.json()['id']}/run",
        json={"prompt": "Review confidential Project Aurora architecture."},
    )
    result.raise_for_status()
    return result.json()


async def verify() -> None:
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://canary") as client:
        trustsplit = await run_mode(client, "trustsplit")
        cloud_only = await run_mode(client, "cloud_only")
        connected = await client.post(
            "/api/sessions",
            json={
                "employee_id": "credential-canary",
                "mode": "trustsplit",
                "trust_zone_id": "personal_cloud",
                "project_id": "project-aurora",
            },
        )
        session_id = connected.json()["id"]
        credential = "sk-proj-CANARY-NEVER-PERSIST"
        response = await client.post(
            f"/api/sessions/{session_id}/provider/connect",
            json={"provider": "openai", "api_credential": credential},
        )

    safe_output = json.dumps(trustsplit)
    leaked = [marker for marker in PRIVATE_MARKERS if marker in safe_output]
    if leaked:
        raise RuntimeError(f"TrustSplit payload leaked private markers: {leaked}")
    if "18,274" not in json.dumps(cloud_only):
        raise RuntimeError("Cloud Only synthetic baseline did not expose its expected canary")
    if credential in response.text:
        raise RuntimeError("Provider credential reappeared in an API response")


def main() -> int:
    asyncio.run(verify())
    print("Secret-egress verification passed (TrustSplit safe; unsafe baseline scoped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import asyncio
import io
import json
import logging
import sys
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.policies import PolicyLoader  # noqa: E402
from app.ledger.repository import ExposureRepository  # noqa: E402
from app.main import create_app  # noqa: E402
from app.orchestration.state_machine import TrustSplitWorkflow  # noqa: E402
from app.privacy.broker import PrivacyBroker  # noqa: E402
from app.private_data.repository import SyntheticPrivateRepository  # noqa: E402
from app.providers.cloud.mock import MockCloudProvider  # noqa: E402
from app.providers.local.mock import MockLocalModelProvider  # noqa: E402

PRIVATE_MARKERS = (
    "Northstar",
    "Oracle RAC",
    "18,274",
    "SettlementEngine",
    "LedgerWriter",
    "AccountPositionDB",
    "CustomerAccountID",
    "Singapore",
    "S$28.4 million",
    "November",
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
    with tempfile.TemporaryDirectory(prefix="trustsplit-canary-") as directory:
        database = Path(directory) / "canary.db"
        repository = ExposureRepository(f"sqlite:///{database}")
        repository.initialize()
        provider = MockCloudProvider()
        policy = PolicyLoader.load(ROOT / "policy" / "default.yaml")
        workflow = TrustSplitWorkflow(
            SyntheticPrivateRepository(ROOT / "data" / "synthetic_project_aurora.json"),
            MockLocalModelProvider(),
            PrivacyBroker(exposure_repository=repository, policy=policy),
            provider,
        )
        log_buffer = io.StringIO()
        handler = logging.StreamHandler(log_buffer)
        logging.getLogger().addHandler(handler)
        try:
            transport = httpx.ASGITransport(
                app=create_app(workflow=workflow, exposure_repository=repository)
            )
            async with httpx.AsyncClient(transport=transport, base_url="http://canary") as client:
                trustsplit = await run_mode(client, "trustsplit")
                cloud_only = await run_mode(client, "cloud_only")
                ledger = await client.get(
                    "/api/ledger",
                    params={
                        "trust_zone_id": "company_cloud",
                        "protected_entity_id": "project-aurora",
                    },
                )
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
        finally:
            logging.getLogger().removeHandler(handler)

        captured = [payload.model_dump(mode="json") for payload in provider.captured_payloads]
        persisted = database.read_bytes().decode("utf-8", errors="ignore")
        safe_output = json.dumps(
            {
                "workflow": trustsplit,
                "provider_captures": captured,
                "ledger": ledger.json(),
                "credential_response": response.json(),
                "logs": log_buffer.getvalue(),
                "database": persisted,
            }
        )
        leaked = [marker for marker in (*PRIVATE_MARKERS, credential) if marker in safe_output]
        if leaked:
            raise RuntimeError(f"TrustSplit surfaces leaked private canaries: {leaked}")
        if len(captured) < 2:
            raise RuntimeError("Expected initial and oracle provider captures")
        if "18,274" not in json.dumps(cloud_only):
            raise RuntimeError("Cloud Only synthetic baseline did not expose its expected canary")


def main() -> int:
    asyncio.run(verify())
    print("Secret-egress verification passed (TrustSplit safe; unsafe baseline scoped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

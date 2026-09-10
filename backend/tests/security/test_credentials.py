import os
from contextlib import contextmanager

import httpx
import pytest

from app.core.credential_vault import CredentialNotFound, CredentialVault
from app.main import create_app


@contextmanager
def company_credential(value: str):
    previous = os.environ.get("COMPANY_CLOUD_API_KEY")
    os.environ["COMPANY_CLOUD_API_KEY"] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("COMPANY_CLOUD_API_KEY", None)
        else:
            os.environ["COMPANY_CLOUD_API_KEY"] = previous


@pytest.mark.anyio
async def test_employee_credential_is_stored_only_in_the_ephemeral_vault() -> None:
    secret = "sk-proj-employeecredentialabcdefghijklmnopqrstuvwxyz"
    vault = CredentialVault()
    transport = httpx.ASGITransport(app=create_app(credential_vault=vault))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        session = await client.post(
            "/api/sessions",
            json={
                "employee_id": "alice",
                "mode": "trustsplit",
                "trust_zone_id": "personal_cloud",
                "project_id": "project-aurora",
            },
        )
        session_id = session.json()["id"]
        connected = await client.post(
            f"/api/sessions/{session_id}/provider/connect",
            json={"provider": "openai", "api_credential": secret},
        )

        assert connected.status_code == 200
        assert connected.json() == {"provider": "openai", "connected": True}
        assert secret not in connected.text
        assert vault.resolve_for_session(session_id).get_secret_value() == secret
        assert secret not in repr(vault)

        disconnected = await client.delete(f"/api/sessions/{session_id}/provider")

    assert disconnected.status_code == 204
    with pytest.raises(CredentialNotFound):
        vault.resolve_for_session(session_id)


@pytest.mark.anyio
async def test_company_credential_never_appears_in_provider_status() -> None:
    secret = "sk-proj-companycredentialabcdefghijklmnopqrstuvwxyz"
    with company_credential(secret):
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/providers/status")

    assert response.status_code == 200
    assert response.json()["company_cloud"]["available"] is True
    assert secret not in response.text

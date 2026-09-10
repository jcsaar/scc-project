import os
from pathlib import Path

from fastapi import FastAPI

from app.api.sessions import create_sessions_router
from app.core.credential_vault import CredentialVault
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.mock import MockCloudProvider
from app.providers.local.mock import MockLocalModelProvider


def create_app(
    workflow: TrustSplitWorkflow | None = None,
    credential_vault: CredentialVault | None = None,
) -> FastAPI:
    app = FastAPI(title="TrustSplit AI", version="0.1.0")
    credential_vault = credential_vault or CredentialVault()

    if workflow is None:
        dataset_path = (
            Path(__file__).resolve().parents[2] / "data" / "synthetic_project_aurora.json"
        )
        workflow = TrustSplitWorkflow(
            private_repository=SyntheticPrivateRepository(dataset_path),
            local_provider=MockLocalModelProvider(),
            broker=PrivacyBroker(),
            cloud_provider=MockCloudProvider(),
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "offline-capable"}

    @app.get("/api/providers/status")
    def provider_status() -> dict[str, dict[str, object]]:
        return {
            "company_cloud": {
                "provider": os.getenv("COMPANY_CLOUD_PROVIDER", "openai"),
                "available": bool(os.getenv("COMPANY_CLOUD_API_KEY")),
            },
            "employee_providers": {"supported": ["openai", "anthropic"]},
        }

    app.include_router(create_sessions_router(workflow, credential_vault))
    return app


app = create_app()

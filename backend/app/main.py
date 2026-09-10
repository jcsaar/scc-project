from pathlib import Path

from fastapi import FastAPI

from app.api.sessions import create_sessions_router
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.mock import MockCloudProvider
from app.providers.local.mock import MockLocalModelProvider


def create_app(workflow: TrustSplitWorkflow | None = None) -> FastAPI:
    app = FastAPI(title="TrustSplit AI", version="0.1.0")

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

    app.include_router(create_sessions_router(workflow))
    return app


app = create_app()

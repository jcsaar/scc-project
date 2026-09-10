import os
from pathlib import Path

from fastapi import FastAPI

from app.api.demo import create_demo_router
from app.api.ledger import create_ledger_router
from app.api.policy import PolicyStore, create_policy_router
from app.api.sessions import create_sessions_router
from app.core.credential_vault import CredentialVault
from app.domain.policies import Policy, PolicyLoader
from app.ledger.repository import ExposureRepository
from app.orchestration.scenarios import DemoScenarioRunner
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.mock import MockCloudProvider
from app.providers.local.mock import MockLocalModelProvider


def create_app(
    workflow: TrustSplitWorkflow | None = None,
    credential_vault: CredentialVault | None = None,
    exposure_repository: ExposureRepository | None = None,
) -> FastAPI:
    app = FastAPI(title="TrustSplit AI", version="0.1.0")
    credential_vault = credential_vault or CredentialVault()
    exposure_repository = exposure_repository or ExposureRepository(
        os.getenv("TRUSTSPLIT_DATABASE_URL", "sqlite://")
    )
    if os.getenv("TRUSTSPLIT_SCHEMA_MANAGED") != "alembic":
        exposure_repository.initialize()
    policy_path = Path(__file__).resolve().parents[2] / "policy" / "default.yaml"
    policy_store = PolicyStore(PolicyLoader.load(policy_path))

    active_broker: PrivacyBroker | None = None
    if workflow is None:
        dataset_path = (
            Path(__file__).resolve().parents[2] / "data" / "synthetic_project_aurora.json"
        )
        active_broker = PrivacyBroker(
            exposure_repository=exposure_repository,
            policy=policy_store.current,
        )
        workflow = TrustSplitWorkflow(
            private_repository=SyntheticPrivateRepository(dataset_path),
            local_provider=MockLocalModelProvider(),
            broker=active_broker,
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

    scenario_runner = DemoScenarioRunner(
        exposure_repository,
        policy_store.current,
        Path(__file__).resolve().parents[2] / "data" / "demo_scenarios",
    )

    app.include_router(
        create_sessions_router(
            workflow,
            credential_vault,
            exposure_repository=exposure_repository,
            policy_provider=lambda: policy_store.current,
        )
    )
    app.include_router(create_demo_router(scenario_runner))
    app.include_router(create_ledger_router(exposure_repository))

    def activate_policy(policy: Policy) -> None:
        if active_broker is not None:
            active_broker.update_policy(policy)
        scenario_runner.update_policy(policy)

    app.include_router(
        create_policy_router(
            policy_store,
            on_replace=activate_policy,
        )
    )
    return app


app = create_app()

from fastapi import APIRouter, HTTPException
from pydantic import Field

from app.domain.disclosures import StrictFrozenModel
from app.orchestration.scenarios import DemoScenarioRunner


class DemoScenarioSummary(StrictFrozenModel):
    id: str
    name: str
    description: str


class DemoScenarioStep(StrictFrozenModel):
    employee: str
    decision: str
    released: str
    risk_after: int = Field(ge=0, le=100)


class DemoScenarioResult(DemoScenarioSummary):
    protected_entity_id: str
    outcome: str
    steps: tuple[DemoScenarioStep, ...]


SCENARIOS = {
    "legitimate": DemoScenarioSummary(
        id="legitimate",
        name="Legitimate collaboration",
        description="A Boolean local-oracle answer improves a safe cloud recommendation.",
    ),
    "mosaic": DemoScenarioSummary(
        id="mosaic",
        name="Cross-employee mosaic",
        description="Related disclosures accumulate across employee sessions.",
    ),
    "malicious_cloud": DemoScenarioSummary(
        id="malicious_cloud",
        name="Malicious narrowing",
        description="A cloud model asks progressively identifying questions.",
    ),
}


def create_demo_router(runner: DemoScenarioRunner) -> APIRouter:
    router = APIRouter(prefix="/api/demo", tags=["demo"])

    @router.get("/scenarios", response_model=list[DemoScenarioSummary])
    def list_scenarios() -> list[DemoScenarioSummary]:
        return list(SCENARIOS.values())

    @router.post("/scenarios/{scenario_id}/run", response_model=DemoScenarioResult)
    async def run_scenario(scenario_id: str) -> DemoScenarioResult:
        scenario = SCENARIOS.get(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Demo scenario not found")
        execution = await runner.run(scenario_id)
        return DemoScenarioResult(
            **scenario.model_dump(),
            protected_entity_id=execution.protected_entity_id,
            outcome=execution.outcome,
            steps=tuple(DemoScenarioStep(**step) for step in execution.steps),
        )

    return router

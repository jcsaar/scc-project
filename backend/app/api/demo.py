from fastapi import APIRouter, HTTPException
from pydantic import Field

from app.domain.disclosures import StrictFrozenModel


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
    outcome: str
    steps: tuple[DemoScenarioStep, ...]


SCENARIOS = {
    "legitimate": DemoScenarioResult(
        id="legitimate",
        name="Legitimate collaboration",
        description="A Boolean local-oracle answer improves a safe cloud recommendation.",
        outcome="Useful advice returned while the hidden constraint stayed local.",
        steps=(
            DemoScenarioStep(
                employee="Alice",
                decision="allow",
                released="Strong consistency required: yes",
                risk_after=8,
            ),
        ),
    ),
    "mosaic": DemoScenarioResult(
        id="mosaic",
        name="Cross-employee mosaic",
        description="Related disclosures accumulate across employee sessions.",
        outcome="Dana's request was denied using the shared trust-zone ledger.",
        steps=(
            DemoScenarioStep(
                employee="Alice", decision="allow", released="High throughput", risk_after=18
            ),
            DemoScenarioStep(
                employee="Bob",
                decision="allow",
                released="Clustered relational database",
                risk_after=34,
            ),
            DemoScenarioStep(
                employee="Charlie",
                decision="generalise",
                released="Account-based partitioning",
                risk_after=57,
            ),
            DemoScenarioStep(employee="Dana", decision="deny", released="Nothing", risk_after=76),
        ),
    ),
    "malicious_cloud": DemoScenarioResult(
        id="malicious_cloud",
        name="Malicious narrowing",
        description="A cloud model asks progressively identifying questions.",
        outcome="The cumulative-risk threshold stopped the narrowing sequence.",
        steps=(
            DemoScenarioStep(
                employee="Cloud", decision="allow", released="Above 10k: yes", risk_after=18
            ),
            DemoScenarioStep(
                employee="Cloud", decision="generalise", released="High throughput", risk_after=36
            ),
            DemoScenarioStep(
                employee="Cloud", decision="generalise", released="15k–20k TPS", risk_after=58
            ),
            DemoScenarioStep(employee="Cloud", decision="deny", released="Nothing", risk_after=78),
        ),
    ),
}


def create_demo_router() -> APIRouter:
    router = APIRouter(prefix="/api/demo", tags=["demo"])

    @router.get("/scenarios", response_model=list[DemoScenarioSummary])
    def list_scenarios() -> list[DemoScenarioSummary]:
        return [
            DemoScenarioSummary(**scenario.model_dump(include={"id", "name", "description"}))
            for scenario in SCENARIOS.values()
        ]

    @router.post("/scenarios/{scenario_id}/run", response_model=DemoScenarioResult)
    def run_scenario(scenario_id: str) -> DemoScenarioResult:
        scenario = SCENARIOS.get(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="Demo scenario not found")
        return scenario

    return router

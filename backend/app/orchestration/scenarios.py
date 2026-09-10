from pathlib import Path
from uuid import uuid4

import yaml

from app.core.limits import CloudRequestLimits, validate_cloud_context_request
from app.domain.disclosures import DisclosureCandidate, DisclosureProposal, PrecisionLevel
from app.domain.policies import Policy
from app.domain.providers import ApprovedCloudPayload
from app.ledger.repository import ExposureRepository
from app.orchestration.state_machine import TrustSplitWorkflow
from app.privacy.broker import BrokerContext, BrokerEvaluation, PrivacyBroker
from app.privacy.risk import RiskEngine, SynergyRule
from app.providers.cloud.malicious_mock import MaliciousMockCloudProvider


class ScenarioExecution:
    def __init__(
        self,
        protected_entity_id: str,
        trust_zone_id: str,
        outcome: str,
        steps: list[dict[str, object]],
    ) -> None:
        self.protected_entity_id = protected_entity_id
        self.trust_zone_id = trust_zone_id
        self.outcome = outcome
        self.steps = steps


class DemoScenarioRunner:
    def __init__(
        self,
        repository: ExposureRepository,
        policy: Policy,
        scenario_directory: Path,
        workflow: TrustSplitWorkflow,
    ) -> None:
        self._repository = repository
        self._policy = policy
        self._scenario_directory = scenario_directory
        self._workflow = workflow

    def update_policy(self, policy: Policy) -> None:
        self._policy = policy

    def reset(self) -> None:
        self._repository.reset_synthetic_demo()

    async def run(self, scenario_id: str) -> ScenarioExecution:
        self._load(scenario_id)
        if scenario_id == "legitimate":
            return await self._legitimate()
        if scenario_id == "mosaic":
            return self._mosaic()
        if scenario_id == "malicious_cloud":
            return await self._malicious()
        raise KeyError(scenario_id)

    def _load(self, scenario_id: str) -> dict[str, object]:
        path = self._scenario_directory / f"{scenario_id}.yaml"
        if not path.is_file():
            raise KeyError(scenario_id)
        definition = yaml.safe_load(path.read_text(encoding="utf-8"))
        if definition.get("synthetic_demo_data") is not True:
            raise ValueError("Demo scenarios must be explicitly marked synthetic")
        return definition

    async def _legitimate(self) -> ScenarioExecution:
        entity = "project-aurora"
        session = self._session("alice", "company_cloud")
        result = await self._workflow.run(
            "Recommend a safe scale-out design.",
            entity,
            "company_cloud",
            session_id=session,
        )
        steps = [
            {
                "employee": evidence.stage.title(),
                "decision": evidence.decision.decision.value,
                "released": evidence.decision.released_text or "Nothing",
                "risk_after": evidence.decision.risk_after,
            }
            for evidence in result.egress_evidence
        ]
        return ScenarioExecution(
            entity,
            "company_cloud",
            (
                "A Boolean oracle answer changed the cloud advice while exact source facts "
                "stayed local."
            ),
            steps,
        )

    def _mosaic(self) -> ScenarioExecution:
        entity = f"synthetic-mosaic-{uuid4()}"
        engine = RiskEngine(
            synergy_rules=(
                SynergyRule(
                    dimension="customer_identity",
                    required_keys=frozenset({"country", "industry", "company_size"}),
                    bonus=12,
                ),
            )
        )
        broker = PrivacyBroker(
            exposure_repository=self._repository,
            policy=self._policy,
            risk_engine=engine,
        )
        inputs = (
            ("Alice", "Southeast Asia", "country", PrecisionLevel.BROAD_CATEGORY, 20),
            ("Bob", "Regulated finance", "industry", PrecisionLevel.BROAD_CATEGORY, 20),
            ("Charlie", "Mid-sized organisation", "company_size", PrecisionLevel.EXACT, 35),
            ("Dana", "Local bank", "local_bank_status", PrecisionLevel.EXACT, 60),
        )
        steps = []
        for employee, text, key, precision, weight in inputs:
            session = self._session(employee.lower(), "personal_cloud")
            evaluation = broker.evaluate(
                self._proposal(text, f"identity.{key}", precision, entity, key),
                BrokerContext(session, "personal_cloud", "customer_identity", weight),
            )
            steps.append(self._step(employee, evaluation))
        return ScenarioExecution(
            entity,
            "personal_cloud",
            "Dana's request was denied using the shared trust-zone ledger.",
            steps,
        )

    async def _malicious(self) -> ScenarioExecution:
        entity = f"synthetic-malicious-{uuid4()}"
        session = self._session("malicious-cloud", "personal_cloud")
        broker = PrivacyBroker(exposure_repository=self._repository, policy=self._policy)
        provider = MaliciousMockCloudProvider()
        initial = broker.evaluate(
            self._proposal(
                "High-throughput transaction design",
                "operations.throughput",
                PrecisionLevel.BROAD_CATEGORY,
                entity,
                "task_context",
            ),
            BrokerContext(session, "personal_cloud", "operations", 8),
        )
        payload = ApprovedCloudPayload(
            provider_name=provider.provider_name,
            trust_zone_id="personal_cloud",
            disclosures=initial.approved_disclosures,
        )
        steps: list[dict[str, object]] = []
        answers = ("Above 10k: yes", "Above 15k: yes", "15k-20k TPS", "Exact value")
        keys = ("threshold_10k", "threshold_15k", "upper_20k", "exact_peak")
        for answer, key in zip(answers, keys, strict=True):
            request = (await provider.send(payload)).context_requests[0]
            validate_cloud_context_request(request, CloudRequestLimits())
            evaluation = broker.evaluate(
                self._proposal(
                    answer,
                    request.category,
                    request.requested_precision,
                    entity,
                    key,
                ),
                BrokerContext(session, "personal_cloud", "operations", 60),
            )
            steps.append(self._step("Cloud", evaluation))
            if not evaluation.approved_disclosures:
                break
            payload = ApprovedCloudPayload(
                provider_name=provider.provider_name,
                trust_zone_id="personal_cloud",
                disclosures=evaluation.approved_disclosures,
            )
        return ScenarioExecution(
            entity,
            "personal_cloud",
            "The cumulative-risk threshold stopped the narrowing sequence.",
            steps,
        )

    def _session(self, employee: str, trust_zone: str) -> str:
        session_id = str(uuid4())
        self._repository.register_session(
            session_id,
            employee,
            trust_zone,
            self._policy.trust_zones[trust_zone].disclosure_budget,
        )
        return session_id

    @staticmethod
    def _proposal(
        text: str,
        category: str,
        precision: PrecisionLevel,
        entity: str,
        key: str,
    ) -> DisclosureProposal:
        alternatives = ()
        if precision in (
            PrecisionLevel.EXACT,
            PrecisionLevel.APPROXIMATE,
            PrecisionLevel.BOUNDED_RANGE,
        ):
            alternatives = (
                DisclosureCandidate(
                    text=f"Lower-precision {category.replace('.', ' ')} indicator",
                    category=category,
                    precision=PrecisionLevel.COARSE_RANGE,
                    fact_keys=(key,),
                ),
            )
        return DisclosureProposal(
            text=text,
            purpose="Execute an explicitly synthetic security scenario",
            category=category,
            requested_precision=precision,
            protected_entity_ids=(entity,),
            fact_keys=(key,),
            alternatives=alternatives,
        )

    @staticmethod
    def _step(employee: str, evaluation: BrokerEvaluation) -> dict[str, object]:
        decision = evaluation.decision
        return {
            "employee": employee,
            "decision": decision.decision.value,
            "released": decision.released_text or "Nothing",
            "risk_after": decision.risk_after,
        }

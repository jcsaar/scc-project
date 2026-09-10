from pydantic import Field

from app.domain.disclosures import BrokerDecision, StrictFrozenModel
from app.domain.providers import ApprovedCloudPayload
from app.domain.workflow import VerificationStatus, WorkflowEvent, WorkflowState
from app.orchestration.events import EventRecorder
from app.privacy.broker import PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.base import CloudProvider
from app.providers.local.base import LocalModelProvider


class WorkflowResult(StrictFrozenModel):
    final_answer: str = Field(min_length=1)
    outbound_payload: ApprovedCloudPayload
    broker_decision: BrokerDecision
    events: tuple[WorkflowEvent, ...] = Field(min_length=1)


class TrustSplitWorkflow:
    def __init__(
        self,
        private_repository: SyntheticPrivateRepository,
        local_provider: LocalModelProvider,
        broker: PrivacyBroker,
        cloud_provider: CloudProvider,
    ) -> None:
        self._private_repository = private_repository
        self._local_provider = local_provider
        self._broker = broker
        self._cloud_provider = cloud_provider

    async def run(self, prompt: str, project_id: str, trust_zone_id: str) -> WorkflowResult:
        events = EventRecorder()
        events.emit(WorkflowState.RECEIVE_PROMPT, "employee", "Private prompt received locally.")

        context = self._private_repository.load_project(project_id)
        events.emit(
            WorkflowState.LOCAL_ANALYSIS,
            "local_ai",
            "Synthetic private context analysed inside the local zone.",
        )

        proposal = self._local_provider.analyse(prompt, context)
        events.emit(
            WorkflowState.CREATE_SAFE_TASK,
            "local_ai",
            "A minimum-information cloud task was proposed.",
        )

        evaluation = self._broker.evaluate(proposal)
        events.emit(
            WorkflowState.BROKER_VALIDATE_OUTBOUND,
            "privacy_broker",
            "The proposed cloud task was authorised.",
        )

        payload = ApprovedCloudPayload(
            provider_name=self._cloud_provider.provider_name,
            trust_zone_id=trust_zone_id,
            disclosures=evaluation.approved_disclosures,
        )
        recommendation = await self._cloud_provider.send(payload)
        events.emit(
            WorkflowState.CLOUD_REASONING,
            "cloud_ai",
            "The cloud reasoned only over the approved payload.",
        )

        verification = self._local_provider.verify(recommendation, context)
        events.emit(
            WorkflowState.LOCAL_VERIFY,
            "local_ai",
            "The cloud recommendation was checked against private constraints.",
        )
        if verification.status is VerificationStatus.REVISION_REQUIRED:
            final_answer = verification.safe_feedback or "A local revision is required."
        else:
            final_answer = verification.final_text or recommendation.text

        events.emit(WorkflowState.FINAL, "local_ai", "Final locally verified answer ready.")
        return WorkflowResult(
            final_answer=final_answer,
            outbound_payload=payload,
            broker_decision=evaluation.decision,
            events=events.events,
        )

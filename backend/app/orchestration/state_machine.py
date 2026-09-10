import httpx
from pydantic import Field

from app.core.limits import CloudRequestLimits, UnsafeCloudRequest, validate_cloud_context_request
from app.domain.disclosures import (
    ApprovedDisclosure,
    BrokerDecision,
    PrecisionLevel,
    StrictFrozenModel,
)
from app.domain.providers import ApprovedCloudPayload
from app.domain.workflow import VerificationStatus, WorkflowEvent, WorkflowState
from app.orchestration.events import EventRecorder
from app.orchestration.oracle import LocalOracle
from app.orchestration.verifier import LocalVerifier
from app.privacy.broker import BrokerContext, PrivacyBroker
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.base import CloudProvider
from app.providers.local.base import LocalModelProvider


class DisclosureEvidence(StrictFrozenModel):
    text: str = Field(min_length=1)
    category: str = Field(min_length=1)
    precision: PrecisionLevel
    fact_keys: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def from_approved(cls, disclosure: ApprovedDisclosure) -> "DisclosureEvidence":
        return cls(**disclosure.model_dump(exclude={"decision_id"}))


class CloudPayloadEvidence(StrictFrozenModel):
    provider_name: str = Field(min_length=1)
    trust_zone_id: str = Field(min_length=1)
    disclosures: tuple[DisclosureEvidence, ...] = Field(min_length=1)

    @classmethod
    def from_approved(cls, payload: ApprovedCloudPayload) -> "CloudPayloadEvidence":
        return cls(
            provider_name=payload.provider_name,
            trust_zone_id=payload.trust_zone_id,
            disclosures=tuple(
                DisclosureEvidence.from_approved(item) for item in payload.disclosures
            ),
        )


class WorkflowResult(StrictFrozenModel):
    final_answer: str = Field(min_length=1)
    outbound_payload: CloudPayloadEvidence | None
    broker_decision: BrokerDecision
    events: tuple[WorkflowEvent, ...] = Field(min_length=1)
    mode: str = "trustsplit"
    exposure_summary: str = "Broker-mediated minimum-information disclosure."


class TrustSplitWorkflow:
    def __init__(
        self,
        private_repository: SyntheticPrivateRepository,
        local_provider: LocalModelProvider,
        broker: PrivacyBroker,
        cloud_provider: CloudProvider,
        max_clarification_rounds: int = 4,
    ) -> None:
        self._private_repository = private_repository
        self._local_provider = local_provider
        self._broker = broker
        self._cloud_provider = cloud_provider
        self._max_clarification_rounds = max_clarification_rounds
        self._oracle = LocalOracle()
        self._request_limits = CloudRequestLimits()
        self._verifier = LocalVerifier()

    async def run(
        self,
        prompt: str,
        project_id: str,
        trust_zone_id: str,
        session_id: str | None = None,
    ) -> WorkflowResult:
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

        broker_context = (
            BrokerContext(
                session_id=session_id,
                trust_zone_id=trust_zone_id,
                dimension=proposal.category.split(".", 1)[0],
                base_weight=15,
            )
            if session_id is not None
            else None
        )
        evaluation = self._broker.evaluate(proposal, broker_context)
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
        try:
            recommendation = await self._cloud_provider.send(payload)
        except (httpx.TimeoutException, TimeoutError):
            events.emit(
                WorkflowState.LOCAL_SYNTHESIS,
                "local_ai",
                "Cloud provider unavailable; completed locally.",
            )
            events.emit(WorkflowState.FINAL, "local_ai", "Final local-only answer ready.")
            return WorkflowResult(
                final_answer=self._verifier.local_fallback(),
                outbound_payload=CloudPayloadEvidence.from_approved(payload),
                broker_decision=evaluation.decision,
                events=events.events,
            )
        events.emit(
            WorkflowState.CLOUD_REASONING,
            "cloud_ai",
            "The cloud reasoned only over the approved payload.",
        )

        clarification_rounds = 0
        while (
            recommendation.context_requests
            and clarification_rounds < self._max_clarification_rounds
        ):
            request = recommendation.context_requests[0]
            events.emit(
                WorkflowState.CLOUD_REQUEST_CONTEXT,
                "cloud_ai",
                "The cloud requested additional private context.",
            )
            try:
                validate_cloud_context_request(request, self._request_limits)
            except UnsafeCloudRequest:
                events.emit(
                    WorkflowState.BROKER_VALIDATE_QUERY,
                    "privacy_broker",
                    "The context request was denied before private lookup.",
                )
                break
            events.emit(
                WorkflowState.BROKER_VALIDATE_QUERY,
                "privacy_broker",
                "The context request was authorised for local evaluation.",
            )
            oracle_proposal = self._oracle.answer(request, context)
            events.emit(
                WorkflowState.LOCAL_ORACLE,
                "local_ai",
                "The local oracle proposed a minimum-information answer.",
            )
            oracle_evaluation = self._broker.evaluate(oracle_proposal)
            events.emit(
                WorkflowState.BROKER_VALIDATE_RESPONSE,
                "privacy_broker",
                "The local oracle answer was independently checked.",
            )
            if not oracle_evaluation.approved_disclosures:
                break
            oracle_payload = ApprovedCloudPayload(
                provider_name=self._cloud_provider.provider_name,
                trust_zone_id=trust_zone_id,
                disclosures=oracle_evaluation.approved_disclosures,
            )
            recommendation = await self._cloud_provider.send(oracle_payload)
            clarification_rounds += 1
            events.emit(
                WorkflowState.CLOUD_CONTINUE,
                "cloud_ai",
                "The cloud continued using only the approved oracle answer.",
            )

        verification = self._local_provider.verify(recommendation, context)
        events.emit(
            WorkflowState.LOCAL_VERIFY,
            "local_ai",
            "The cloud recommendation was checked against private constraints.",
        )
        if verification.status is VerificationStatus.REVISION_REQUIRED:
            feedback = verification.safe_feedback or "Preserve mandatory local constraints."
            revision = self._broker.evaluate(
                self._verifier.revision_proposal(feedback, context.project_id)
            )
            revision_payload = ApprovedCloudPayload(
                provider_name=self._cloud_provider.provider_name,
                trust_zone_id=trust_zone_id,
                disclosures=revision.approved_disclosures,
            )
            events.emit(
                WorkflowState.CLOUD_REVISION,
                "privacy_broker",
                "A safe constraint message requested a cloud revision.",
            )
            try:
                recommendation = await self._cloud_provider.send(revision_payload)
                revised = self._local_provider.verify(recommendation, context)
                final_answer = (
                    revised.final_text
                    if revised.status is VerificationStatus.ACCEPTED
                    else self._verifier.local_fallback()
                )
            except (httpx.TimeoutException, TimeoutError):
                events.emit(
                    WorkflowState.LOCAL_SYNTHESIS,
                    "local_ai",
                    "Cloud revision unavailable; completed locally.",
                )
                final_answer = self._verifier.local_fallback()
        else:
            final_answer = verification.final_text or recommendation.text

        events.emit(WorkflowState.FINAL, "local_ai", "Final locally verified answer ready.")
        return WorkflowResult(
            final_answer=final_answer,
            outbound_payload=CloudPayloadEvidence.from_approved(payload),
            broker_decision=evaluation.decision,
            events=events.events,
        )

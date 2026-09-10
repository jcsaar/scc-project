import json
from threading import RLock

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
from app.orchestration.progress import DemoProgressEmitter, PresentationClock, ProgressStage
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


class EgressEvidence(StrictFrozenModel):
    stage: str = Field(min_length=1)
    decision: BrokerDecision
    payload: CloudPayloadEvidence | None = None


class WorkflowResult(StrictFrozenModel):
    final_answer: str = Field(min_length=1)
    outbound_payload: CloudPayloadEvidence | None
    outbound_payloads: tuple[CloudPayloadEvidence, ...] = ()
    egress_evidence: tuple[EgressEvidence, ...] = ()
    broker_decision: BrokerDecision
    events: tuple[WorkflowEvent, ...] = Field(min_length=1)
    mode: str = "trustsplit"
    exposure_summary: str = "Broker-mediated minimum-information disclosure."
    session_budget_remaining: int | None = Field(default=None, ge=0)
    final_risk: int = Field(default=0, ge=0, le=100)
    verification_status: str = "not_applicable"


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
        self._config_lock = RLock()
        self._oracle = LocalOracle()
        self._request_limits = CloudRequestLimits()
        self._verifier = LocalVerifier()

    def update_max_clarification_rounds(self, value: int) -> None:
        with self._config_lock:
            self._max_clarification_rounds = value

    async def run(
        self,
        prompt: str,
        project_id: str,
        trust_zone_id: str,
        session_id: str | None = None,
        progress_emitter: DemoProgressEmitter | None = None,
    ) -> WorkflowResult:
        events = EventRecorder()
        progress = progress_emitter or DemoProgressEmitter(clock=PresentationClock(scale=0))
        outbound_payloads: list[CloudPayloadEvidence] = []
        egress_evidence: list[EgressEvidence] = []
        with self._config_lock:
            max_clarification_rounds = self._max_clarification_rounds
        await progress.emit(
            ProgressStage.LOCAL_READ,
            "Reading your request locally…",
            "Private prompt received inside the local zone.",
        )
        events.emit(WorkflowState.RECEIVE_PROMPT, "employee", "Private prompt received locally.")

        context = self._private_repository.load_project(project_id)
        await progress.emit(
            ProgressStage.SENSITIVE_SCAN,
            "Scanning for sensitive information…",
            "Protected entities and exact source facts remain local.",
        )
        events.emit(
            WorkflowState.LOCAL_ANALYSIS,
            "local_ai",
            "Synthetic private context analysed inside the local zone.",
        )

        proposal = self._local_provider.analyse(prompt, context)
        await progress.emit(
            ProgressStage.SAFE_RECONSTRUCTION,
            "Reconstructing a safe prompt…",
            "A minimum-information representation was prepared.",
            terminal_detail=self._reconstruction_detail(context, proposal),
        )
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
        await progress.emit(
            ProgressStage.PRIVACY_BORDER,
            "Checking the zero-trust privacy border…",
            f"Broker decision: {evaluation.decision.decision.value.upper()} with risk "
            f"{evaluation.decision.risk_before} → {evaluation.decision.risk_after}.",
            terminal_detail=(
                f"Decision: {evaluation.decision.decision.value.upper()} | Risk: "
                f"{evaluation.decision.risk_before} -> {evaluation.decision.risk_after} | "
                f"Budget cost: {evaluation.decision.budget_cost}"
            ),
        )
        if not evaluation.approved_disclosures:
            egress_evidence.append(EgressEvidence(stage="initial", decision=evaluation.decision))
            events.emit(
                WorkflowState.BROKER_VALIDATE_OUTBOUND,
                "privacy_broker",
                "The proposed cloud task was denied.",
            )
            events.emit(
                WorkflowState.LOCAL_SYNTHESIS,
                "local_ai",
                "Disclosure denied; completed locally.",
            )
            events.emit(WorkflowState.FINAL, "local_ai", "Final local-only answer ready.")
            await progress.emit(
                ProgressStage.RETURN_RESPONSE,
                "Sending the safe response to you…",
                "Cloud transmission was blocked; a local fallback is ready.",
            )
            return WorkflowResult(
                final_answer=self._verifier.local_fallback(),
                outbound_payload=None,
                outbound_payloads=(),
                egress_evidence=tuple(egress_evidence),
                broker_decision=evaluation.decision,
                events=events.events,
                final_risk=evaluation.decision.risk_after,
                verification_status=VerificationStatus.LOCAL_ONLY.value,
            )
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
        primary_evidence = CloudPayloadEvidence.from_approved(payload)
        outbound_payloads.append(primary_evidence)
        egress_evidence.append(
            EgressEvidence(stage="initial", decision=evaluation.decision, payload=primary_evidence)
        )
        await progress.emit(
            ProgressStage.CLOUD_SEND,
            "Sending approved context to Cloud AI…",
            "Only the immutable broker-approved envelope will leave the device.",
            terminal_detail=(
                "[CLOUD PAYLOAD] "
                + json.dumps(primary_evidence.model_dump(mode="json"), separators=(",", ":"))
            ),
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
            await progress.emit(
                ProgressStage.RETURN_RESPONSE,
                "Sending the safe response to you…",
                "Cloud was unavailable; a local fallback is ready.",
            )
            return WorkflowResult(
                final_answer=self._verifier.local_fallback(),
                outbound_payload=primary_evidence,
                outbound_payloads=tuple(outbound_payloads),
                egress_evidence=tuple(egress_evidence),
                broker_decision=evaluation.decision,
                events=events.events,
                final_risk=max(item.decision.risk_after for item in egress_evidence),
                verification_status=VerificationStatus.LOCAL_ONLY.value,
            )
        events.emit(
            WorkflowState.CLOUD_REASONING,
            "cloud_ai",
            "The cloud reasoned only over the approved payload.",
        )
        await progress.emit(
            ProgressStage.CLOUD_REASONING,
            "Cloud AI is reasoning…",
            "Cloud reasoning is limited to the approved payload.",
        )

        clarification_rounds = 0
        while recommendation.context_requests and clarification_rounds < max_clarification_rounds:
            request = recommendation.context_requests[0]
            events.emit(
                WorkflowState.CLOUD_REQUEST_CONTEXT,
                "cloud_ai",
                "The cloud requested additional private context.",
            )
            await progress.emit(
                ProgressStage.CLOUD_REASONING,
                "Cloud AI requested one privacy-safe clarification…",
                "The local oracle will answer without releasing exact source facts.",
                delay_ms=0,
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
            oracle_context = (
                BrokerContext(
                    session_id=session_id,
                    trust_zone_id=trust_zone_id,
                    dimension=oracle_proposal.category.split(".", 1)[0],
                    base_weight=12,
                )
                if session_id is not None
                else None
            )
            oracle_evaluation = self._broker.evaluate(oracle_proposal, oracle_context)
            events.emit(
                WorkflowState.BROKER_VALIDATE_RESPONSE,
                "privacy_broker",
                "The local oracle answer was independently checked.",
            )
            if not oracle_evaluation.approved_disclosures:
                egress_evidence.append(
                    EgressEvidence(stage="clarification", decision=oracle_evaluation.decision)
                )
                break
            oracle_payload = ApprovedCloudPayload(
                provider_name=self._cloud_provider.provider_name,
                trust_zone_id=trust_zone_id,
                disclosures=oracle_evaluation.approved_disclosures,
            )
            oracle_evidence = CloudPayloadEvidence.from_approved(oracle_payload)
            outbound_payloads.append(oracle_evidence)
            egress_evidence.append(
                EgressEvidence(
                    stage="clarification",
                    decision=oracle_evaluation.decision,
                    payload=oracle_evidence,
                )
            )
            await progress.emit(
                ProgressStage.CLOUD_SEND,
                "Sending the approved clarification to Cloud AI…",
                "Only the broker-approved Boolean answer is leaving the device.",
                terminal_detail=(
                    "[CLOUD PAYLOAD] "
                    + json.dumps(oracle_evidence.model_dump(mode="json"), separators=(",", ":"))
                ),
                delay_ms=0,
            )
            try:
                recommendation = await self._cloud_provider.send(oracle_payload)
            except (httpx.TimeoutException, TimeoutError):
                events.emit(
                    WorkflowState.LOCAL_SYNTHESIS,
                    "local_ai",
                    "Cloud clarification unavailable; completed locally.",
                )
                events.emit(WorkflowState.FINAL, "local_ai", "Final local-only answer ready.")
                return WorkflowResult(
                    final_answer=self._verifier.local_fallback(),
                    outbound_payload=primary_evidence,
                    outbound_payloads=tuple(outbound_payloads),
                    egress_evidence=tuple(egress_evidence),
                    broker_decision=evaluation.decision,
                    events=events.events,
                    final_risk=max(item.decision.risk_after for item in egress_evidence),
                    verification_status=VerificationStatus.LOCAL_ONLY.value,
                )
            clarification_rounds += 1
            events.emit(
                WorkflowState.CLOUD_CONTINUE,
                "cloud_ai",
                "The cloud continued using only the approved oracle answer.",
            )

        await progress.emit(
            ProgressStage.LOCAL_VERIFY,
            "Verifying the response locally…",
            "The recommendation is checked against hidden local constraints.",
        )
        verification = self._local_provider.verify(recommendation, context)
        events.emit(
            WorkflowState.LOCAL_VERIFY,
            "local_ai",
            "The cloud recommendation was checked against private constraints.",
        )
        if verification.status is VerificationStatus.REVISION_REQUIRED:
            feedback = verification.safe_feedback or "Preserve mandatory local constraints."
            revision_proposal = self._verifier.revision_proposal(feedback, context.project_id)
            revision_context = (
                BrokerContext(
                    session_id=session_id,
                    trust_zone_id=trust_zone_id,
                    dimension="architecture",
                    base_weight=10,
                )
                if session_id is not None
                else None
            )
            revision = self._broker.evaluate(revision_proposal, revision_context)
            if not revision.approved_disclosures:
                egress_evidence.append(EgressEvidence(stage="revision", decision=revision.decision))
                events.emit(
                    WorkflowState.LOCAL_SYNTHESIS,
                    "local_ai",
                    "Revision disclosure denied; completed locally.",
                )
                final_answer = self._verifier.local_fallback()
                events.emit(WorkflowState.FINAL, "local_ai", "Final local-only answer ready.")
                return WorkflowResult(
                    final_answer=final_answer,
                    outbound_payload=primary_evidence,
                    outbound_payloads=tuple(outbound_payloads),
                    egress_evidence=tuple(egress_evidence),
                    broker_decision=evaluation.decision,
                    events=events.events,
                    final_risk=max(item.decision.risk_after for item in egress_evidence),
                    verification_status=VerificationStatus.LOCAL_ONLY.value,
                )
            revision_payload = ApprovedCloudPayload(
                provider_name=self._cloud_provider.provider_name,
                trust_zone_id=trust_zone_id,
                disclosures=revision.approved_disclosures,
            )
            revision_evidence = CloudPayloadEvidence.from_approved(revision_payload)
            outbound_payloads.append(revision_evidence)
            egress_evidence.append(
                EgressEvidence(
                    stage="revision",
                    decision=revision.decision,
                    payload=revision_evidence,
                )
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
            final_verification_status = (
                VerificationStatus.ACCEPTED.value
                if final_answer != self._verifier.local_fallback()
                else VerificationStatus.LOCAL_ONLY.value
            )
        else:
            final_answer = verification.final_text or recommendation.text
            final_verification_status = VerificationStatus.ACCEPTED.value

        events.emit(WorkflowState.FINAL, "local_ai", "Final locally verified answer ready.")
        await progress.emit(
            ProgressStage.RETURN_RESPONSE,
            "Sending the verified response to you…",
            "The locally verified answer is ready for the chat.",
        )
        return WorkflowResult(
            final_answer=final_answer,
            outbound_payload=primary_evidence,
            outbound_payloads=tuple(outbound_payloads),
            egress_evidence=tuple(egress_evidence),
            broker_decision=evaluation.decision,
            events=events.events,
            final_risk=max(item.decision.risk_after for item in egress_evidence),
            verification_status=final_verification_status,
        )

    @staticmethod
    def _reconstruction_detail(context, proposal) -> str:
        details = []
        for key in proposal.fact_keys:
            fact = next((item for item in context.facts if item.semantic_key == key), None)
            if fact is None:
                continue
            safe_value = fact.generalizations.get(proposal.requested_precision.value)
            if safe_value is None:
                safe_value = next(iter(fact.generalizations.values()), "withheld")
            details.append(f"{fact.raw_value} -> {safe_value}")
        return (
            " | ".join(details) or "Local reconstruction completed; source facts were not exported."
        )

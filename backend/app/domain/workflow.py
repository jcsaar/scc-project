from enum import StrEnum

from pydantic import Field

from app.domain.disclosures import StrictFrozenModel


class WorkflowState(StrEnum):
    RECEIVE_PROMPT = "receive_prompt"
    LOCAL_ANALYSIS = "local_analysis"
    CREATE_SAFE_TASK = "create_safe_task"
    BROKER_VALIDATE_OUTBOUND = "broker_validate_outbound"
    CLOUD_REASONING = "cloud_reasoning"
    CLOUD_REQUEST_CONTEXT = "cloud_request_context"
    BROKER_VALIDATE_QUERY = "broker_validate_query"
    LOCAL_ORACLE = "local_oracle"
    BROKER_VALIDATE_RESPONSE = "broker_validate_response"
    CLOUD_CONTINUE = "cloud_continue"
    LOCAL_VERIFY = "local_verify"
    CLOUD_REVISION = "cloud_revision"
    LOCAL_SYNTHESIS = "local_synthesis"
    FINAL = "final"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VerificationStatus(StrEnum):
    ACCEPTED = "accepted"
    REVISION_REQUIRED = "revision_required"
    LOCAL_ONLY = "local_only"


class VerificationResult(StrictFrozenModel):
    status: VerificationStatus
    safe_feedback: str | None = None
    final_text: str | None = None


class WorkflowEvent(StrictFrozenModel):
    sequence: int = Field(ge=1)
    state: WorkflowState
    actor: str = Field(min_length=1)
    safe_summary: str = Field(min_length=1)

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.orchestration.state_machine import TrustSplitWorkflow, WorkflowResult


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSessionRequest(ApiModel):
    employee_id: str = Field(min_length=1)
    mode: str = Field(pattern="^trustsplit$")
    trust_zone_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)


class SessionResponse(ApiModel):
    id: str
    employee_id: str
    mode: str
    trust_zone_id: str
    project_id: str


class RunWorkflowRequest(ApiModel):
    prompt: str = Field(min_length=1, max_length=20_000)


def create_sessions_router(workflow: TrustSplitWorkflow) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])
    sessions: dict[str, SessionResponse] = {}

    @router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
    def create_session(request: CreateSessionRequest) -> SessionResponse:
        session = SessionResponse(id=str(uuid4()), **request.model_dump())
        sessions[session.id] = session
        return session

    @router.post("/{session_id}/run", response_model=WorkflowResult)
    async def run_session(session_id: str, request: RunWorkflowRequest) -> WorkflowResult:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return await workflow.run(
            prompt=request.prompt,
            project_id=session.project_id,
            trust_zone_id=session.trust_zone_id,
        )

    return router

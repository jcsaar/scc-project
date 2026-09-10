from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core.credential_vault import CredentialVault
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


class ConnectProviderRequest(ApiModel):
    provider: str = Field(pattern="^(openai|anthropic)$")
    api_credential: SecretStr


class ProviderConnectionResponse(ApiModel):
    provider: str
    connected: bool


def create_sessions_router(
    workflow: TrustSplitWorkflow, credential_vault: CredentialVault
) -> APIRouter:
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

    @router.post("/{session_id}/provider/connect", response_model=ProviderConnectionResponse)
    def connect_provider(
        session_id: str, request: ConnectProviderRequest
    ) -> ProviderConnectionResponse:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        credential_vault.put(session_id, request.provider, request.api_credential)
        return ProviderConnectionResponse(provider=request.provider, connected=True)

    @router.delete("/{session_id}/provider", status_code=status.HTTP_204_NO_CONTENT)
    def disconnect_provider(session_id: str) -> Response:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        credential_vault.delete_session(session_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router

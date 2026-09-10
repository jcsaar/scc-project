import asyncio
import json
import os
from collections.abc import Callable
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.core.credential_vault import CredentialVault
from app.domain.policies import Policy
from app.ledger.repository import ExposureRepository
from app.orchestration.demo_modes import DemoModeRunner
from app.orchestration.progress import DemoProgressEmitter, PresentationClock
from app.orchestration.state_machine import TrustSplitWorkflow, WorkflowResult
from app.presentation.terminal import TerminalPresenter


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateSessionRequest(ApiModel):
    employee_id: str = Field(min_length=1)
    mode: str = Field(pattern="^(trustsplit|cloud_only|local_only|basic_redaction)$")
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
    workflow: TrustSplitWorkflow,
    credential_vault: CredentialVault,
    demo_runner: DemoModeRunner | None = None,
    exposure_repository: ExposureRepository | None = None,
    policy_provider: Callable[[], Policy] | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])
    sessions: dict[str, SessionResponse] = {}
    results: dict[str, WorkflowResult] = {}

    def progress_scale() -> float:
        raw = os.getenv("TRUSTSPLIT_DEMO_DELAY_SCALE", "0")
        try:
            scale = float(raw)
        except ValueError as error:
            raise HTTPException(
                status_code=500, detail="Invalid demo delay configuration"
            ) from error
        if not 0 <= scale <= 2:
            raise HTTPException(status_code=500, detail="Invalid demo delay configuration")
        return scale

    @router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
    def create_session(request: CreateSessionRequest) -> SessionResponse:
        session = SessionResponse(id=str(uuid4()), **request.model_dump())
        if exposure_repository is not None and policy_provider is not None:
            zone = policy_provider().trust_zones.get(session.trust_zone_id)
            if zone is None:
                raise HTTPException(status_code=422, detail="Unknown provider trust zone")
            exposure_repository.register_session(
                session.id,
                session.employee_id,
                session.trust_zone_id,
                zone.disclosure_budget,
            )
        sessions[session.id] = session
        return session

    @router.post("/{session_id}/run", response_model=WorkflowResult)
    async def run_session(session_id: str, request: RunWorkflowRequest) -> WorkflowResult:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        runner = demo_runner or DemoModeRunner(workflow)
        result = await runner.run(
            mode=session.mode,
            prompt=request.prompt,
            project_id=session.project_id,
            trust_zone_id=session.trust_zone_id,
            session_id=session.id,
        )
        if exposure_repository is not None:
            result = result.model_copy(
                update={
                    "session_budget_remaining": exposure_repository.remaining_budget(session.id)
                }
            )
        results[session_id] = result
        return result

    @router.post("/{session_id}/run-stream")
    async def run_session_stream(session_id: str, request: RunWorkflowRequest) -> StreamingResponse:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        queue: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
        terminal = TerminalPresenter()

        async def on_progress(event: object) -> None:
            await queue.put(("progress", event))

        emitter = DemoProgressEmitter(
            stream_sink=on_progress,
            terminal_sink=terminal,
            private_terminal_sink=terminal.private,
            clock=PresentationClock(scale=progress_scale()),
        )

        async def execute() -> None:
            try:
                runner = demo_runner or DemoModeRunner(workflow)
                result = await runner.run(
                    mode=session.mode,
                    prompt=request.prompt,
                    project_id=session.project_id,
                    trust_zone_id=session.trust_zone_id,
                    session_id=session.id,
                    progress_emitter=emitter,
                )
                if exposure_repository is not None:
                    result = result.model_copy(
                        update={
                            "session_budget_remaining": exposure_repository.remaining_budget(
                                session.id
                            )
                        }
                    )
                results[session_id] = result
                await queue.put(("result", result))
            except Exception as error:  # pragma: no cover - exercised through stream contract
                await queue.put(("error", str(error)))

        task = asyncio.create_task(execute())

        async def stream():
            try:
                while True:
                    kind, value = await queue.get()
                    if kind == "progress" or kind == "result":
                        data = value.model_dump(mode="json")
                    else:
                        data = {"detail": value}
                    yield f"event: {kind}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
                    if kind in {"result", "error"}:
                        break
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.get("/{session_id}")
    def session_status(session_id: str) -> dict[str, str]:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"id": session_id, "status": "complete" if session_id in results else "ready"}

    @router.get("/{session_id}/events")
    def session_events(session_id: str, after_sequence: int = 0) -> StreamingResponse:
        result = results.get(session_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Workflow result not found")

        def stream():
            for item in result.events:
                if item.sequence > after_sequence:
                    data = json.dumps(item.model_dump(mode="json"), separators=(",", ":"))
                    yield f"id: {item.sequence}\ndata: {data}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

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

from app.domain.workflow import WorkflowEvent, WorkflowState


class EventRecorder:
    def __init__(self) -> None:
        self._events: list[WorkflowEvent] = []

    def emit(self, state: WorkflowState, actor: str, safe_summary: str) -> None:
        self._events.append(
            WorkflowEvent(
                sequence=len(self._events) + 1,
                state=state,
                actor=actor,
                safe_summary=safe_summary,
            )
        )

    @property
    def events(self) -> tuple[WorkflowEvent, ...]:
        return tuple(self._events)

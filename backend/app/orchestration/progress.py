from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from enum import StrEnum

from pydantic import Field

from app.domain.disclosures import StrictFrozenModel


class ProgressStage(StrEnum):
    LOCAL_READ = "local_read"
    SENSITIVE_SCAN = "sensitive_scan"
    SAFE_RECONSTRUCTION = "safe_reconstruction"
    PRIVACY_BORDER = "privacy_border"
    CLOUD_SEND = "cloud_send"
    CLOUD_REASONING = "cloud_reasoning"
    LOCAL_VERIFY = "local_verify"
    RETURN_RESPONSE = "return_response"


class ProgressEvent(StrictFrozenModel):
    sequence: int = Field(ge=1)
    stage: ProgressStage
    public_label: str = Field(min_length=1)
    safe_summary: str = Field(min_length=1)
    delay_ms: int = Field(ge=0, le=3000)


ProgressSink = Callable[[ProgressEvent], Awaitable[None] | None]
PrivateTerminalSink = Callable[[str], Awaitable[None] | None]


class PresentationClock:
    def __init__(self, scale: float = 1.0) -> None:
        if not 0 <= scale <= 2:
            raise ValueError("Presentation delay scale must be between 0 and 2")
        self.scale = scale

    async def wait(self, delay_ms: int) -> None:
        if self.scale:
            await asyncio.sleep(delay_ms / 1000 * self.scale)


class DemoProgressEmitter:
    _delays = {
        ProgressStage.LOCAL_READ: 1200,
        ProgressStage.SENSITIVE_SCAN: 1500,
        ProgressStage.SAFE_RECONSTRUCTION: 1750,
        ProgressStage.PRIVACY_BORDER: 1600,
        ProgressStage.CLOUD_SEND: 1200,
        ProgressStage.CLOUD_REASONING: 1800,
        ProgressStage.LOCAL_VERIFY: 1450,
        ProgressStage.RETURN_RESPONSE: 750,
    }

    def __init__(
        self,
        stream_sink: ProgressSink | None = None,
        terminal_sink: ProgressSink | None = None,
        private_terminal_sink: PrivateTerminalSink | None = None,
        clock: PresentationClock | None = None,
    ) -> None:
        self._stream_sink = stream_sink
        self._terminal_sink = terminal_sink
        self._private_terminal_sink = private_terminal_sink
        self._clock = clock or PresentationClock()
        self._sequence = 0

    async def emit(
        self,
        stage: ProgressStage,
        public_label: str,
        safe_summary: str,
        terminal_detail: str | None = None,
        delay_ms: int | None = None,
    ) -> ProgressEvent:
        actual_delay = self._delays[stage] if delay_ms is None else delay_ms
        await self._clock.wait(actual_delay)
        self._sequence += 1
        event = ProgressEvent(
            sequence=self._sequence,
            stage=stage,
            public_label=public_label,
            safe_summary=safe_summary,
            delay_ms=actual_delay,
        )
        for sink in (self._stream_sink, self._terminal_sink):
            if sink is not None:
                result = sink(event)
                if inspect.isawaitable(result):
                    await result
        if terminal_detail is not None and self._private_terminal_sink is not None:
            result = self._private_terminal_sink(terminal_detail)
            if inspect.isawaitable(result):
                await result
        return event

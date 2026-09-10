from __future__ import annotations

import os
import sys
from typing import TextIO

from app.orchestration.progress import ProgressEvent, ProgressStage


class TerminalPresenter:
    """Render the same public progress events used by the browser to a TTY."""

    _labels = {
        ProgressStage.LOCAL_READ: "LOCAL AI",
        ProgressStage.SENSITIVE_SCAN: "LOCAL AI",
        ProgressStage.SAFE_RECONSTRUCTION: "RECONSTRUCTOR",
        ProgressStage.PRIVACY_BORDER: "PRIVACY BORDER",
        ProgressStage.CLOUD_SEND: "CLOUD PAYLOAD",
        ProgressStage.CLOUD_REASONING: "CLOUD AI",
        ProgressStage.LOCAL_VERIFY: "LOCAL AI",
        ProgressStage.RETURN_RESPONSE: "FINAL",
    }
    _colours = {
        ProgressStage.LOCAL_READ: "36",
        ProgressStage.SENSITIVE_SCAN: "36",
        ProgressStage.SAFE_RECONSTRUCTION: "33",
        ProgressStage.PRIVACY_BORDER: "35",
        ProgressStage.CLOUD_SEND: "34",
        ProgressStage.CLOUD_REASONING: "34",
        ProgressStage.LOCAL_VERIFY: "32",
        ProgressStage.RETURN_RESPONSE: "32",
    }

    def __init__(self, stream: TextIO | None = None, private_trace: bool | None = None) -> None:
        self._stream = stream or sys.stdout
        self._colour = bool(getattr(self._stream, "isatty", lambda: False)())
        self._private_trace = (
            os.getenv("TRUSTSPLIT_DEMO_PRIVATE_TRACE") == "1"
            if private_trace is None
            else private_trace
        )

    def __call__(self, event: ProgressEvent) -> None:
        label = self._labels[event.stage]
        line = f"[{label}] {event.public_label} — {event.safe_summary}"
        self._write(line, self._colours[event.stage])

    def private(self, detail: str) -> None:
        if detail.startswith("[CLOUD PAYLOAD]"):
            self._write(detail, "34")
        elif self._private_trace:
            self._write(f"[LOCAL PRIVATE] {detail}", "90")

    def _write(self, line: str, colour: str) -> None:
        if self._colour:
            self._stream.write(f"\033[{colour}m{line}\033[0m\n")
        else:
            self._stream.write(line + "\n")
        self._stream.flush()

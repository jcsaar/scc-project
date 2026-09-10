import pytest

from app.orchestration.progress import DemoProgressEmitter, PresentationClock, ProgressStage


@pytest.mark.anyio
async def test_emitter_sends_one_identical_event_to_stream_and_terminal() -> None:
    streamed, terminal = [], []
    emitter = DemoProgressEmitter(
        stream_sink=streamed.append,
        terminal_sink=terminal.append,
        clock=PresentationClock(scale=0),
    )

    event = await emitter.emit(
        ProgressStage.PRIVACY_BORDER,
        "Checking the zero-trust privacy border…",
        "Broker evaluated the approved candidate.",
    )

    assert streamed == [event]
    assert terminal == [event]
    assert event.sequence == 1
    assert event.delay_ms == 1600


@pytest.mark.anyio
async def test_private_terminal_detail_is_not_part_of_public_event() -> None:
    private = []
    emitter = DemoProgressEmitter(
        private_terminal_sink=private.append,
        clock=PresentationClock(scale=0),
    )

    event = await emitter.emit(
        ProgressStage.SAFE_RECONSTRUCTION,
        "Reconstructing a safe prompt…",
        "A minimum-information prompt was prepared.",
        terminal_detail="18,274 TPS -> 15k-20k TPS",
    )

    assert private == ["18,274 TPS -> 15k-20k TPS"]
    assert "18,274" not in event.model_dump_json()


@pytest.mark.anyio
async def test_zero_scale_clock_does_not_sleep() -> None:
    await PresentationClock(scale=0).wait(1500)


@pytest.mark.anyio
async def test_default_demo_timing_is_long_enough_to_show_each_privacy_stage() -> None:
    events = []
    emitter = DemoProgressEmitter(stream_sink=events.append, clock=PresentationClock(scale=0))

    for stage in (
        ProgressStage.LOCAL_READ,
        ProgressStage.SENSITIVE_SCAN,
        ProgressStage.SAFE_RECONSTRUCTION,
        ProgressStage.PRIVACY_BORDER,
        ProgressStage.CLOUD_SEND,
        ProgressStage.CLOUD_REASONING,
        ProgressStage.LOCAL_VERIFY,
        ProgressStage.RETURN_RESPONSE,
    ):
        await emitter.emit(stage, stage.value, "demo")

    assert [event.delay_ms for event in events] == [1200, 1500, 1750, 1600, 1200, 1800, 1450, 750]
    assert sum(event.delay_ms for event in events) == 11250

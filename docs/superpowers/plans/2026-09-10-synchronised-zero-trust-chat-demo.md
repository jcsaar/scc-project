# Synchronised Zero-Trust Chat Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a deterministic ChatGPT-style POC whose browser thinking states and local terminal trace visibly demonstrate the same zero-trust privacy-border workflow.

**Architecture:** Introduce a small presentation-event layer around the existing workflow. A streamed session endpoint publishes safe progress events to the React client while the same event objects drive a terminal presenter; private terminal-only transformation details are opt-in and never enter the HTTP event. Deterministic providers and broker decisions remain the functional core.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, asyncio/SSE, SQLAlchemy, React 19, TypeScript, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-10-synchronised-zero-trust-demo-design.md`

## Global Constraints

- Normal-run presentation time is 8–12 seconds; the complete narrated demo is 3–4 minutes.
- Browser and terminal must be driven by the same ordered progress events.
- Status text describes observable operations and never exposes chain-of-thought.
- Real provider calls are out of scope; all model responses stay deterministic.
- Private terminal detail is disabled unless `TRUSTSPLIT_DEMO_PRIVATE_TRACE=1`.
- Delays are disabled in automated tests through dependency injection, not patched sleeps.
- No source secret may enter a cloud payload, browser response, or persistent application log.

---

### Task 1: Define the shared progress-event contract

**Files:**
- Create: `backend/app/orchestration/progress.py`
- Test: `backend/tests/orchestration/test_progress.py`

**Interfaces:**
- Produces: `ProgressStage`, `ProgressEvent`, `ProgressSink`, `PresentationClock`, and `DemoProgressEmitter.emit(stage, public_label, safe_summary, terminal_detail=None)`.
- Consumes: no application services; this module remains independent of the broker and providers.

- [ ] **Step 1: Write failing contract tests**

```python
async def test_emitter_sends_one_identical_event_to_stream_and_terminal():
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


async def test_zero_scale_clock_does_not_sleep():
    clock = PresentationClock(scale=0)
    await clock.wait(1500)
```

- [ ] **Step 2: Run the tests and confirm they fail because `progress.py` does not exist**

Run: `cd backend && .venv/bin/pytest tests/orchestration/test_progress.py -q`

- [ ] **Step 3: Implement the event types and injected clock**

```python
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
```

Use the timing table `900, 1200, 1400, 1300, 900, 1500, 1200, 600` milliseconds. `PresentationClock(scale=0)` skips sleeps; `scale=1` sleeps for the declared duration.

- [ ] **Step 4: Run tests and lint**

Run: `cd backend && .venv/bin/pytest tests/orchestration/test_progress.py -q && .venv/bin/python -m ruff check app tests`

- [ ] **Step 5: Commit**

```bash
git add backend/app/orchestration/progress.py backend/tests/orchestration/test_progress.py
git commit -m "feat: define synchronized demo progress events"
```

### Task 2: Drive workflow stages and safe terminal output

**Files:**
- Create: `backend/app/presentation/terminal.py`
- Modify: `backend/app/orchestration/state_machine.py`
- Modify: `backend/app/privacy/broker.py`
- Test: `backend/tests/integration/test_progress_trace.py`
- Test: `backend/tests/privacy/test_live_policy.py`

**Interfaces:**
- Consumes: `DemoProgressEmitter` from Task 1 and existing broker-approved `CloudPayloadEvidence`.
- Produces: `TerminalPresenter.__call__(event: ProgressEvent) -> None` and optional `progress_emitter` argument on `TrustSplitWorkflow.run(...)`.

- [ ] **Step 1: Write a failing synchronized-flow test**

```python
@pytest.mark.anyio
async def test_normal_run_emits_expected_safe_stages(workflow):
    browser_events, terminal_events = [], []
    emitter = DemoProgressEmitter(
        browser_events.append, terminal_events.append, PresentationClock(scale=0)
    )
    result = await workflow.run(
        "Review Project Aurora", "project-aurora", "company_cloud",
        session_id="session-1", progress_emitter=emitter,
    )
    assert [event.stage for event in browser_events] == [
        ProgressStage.LOCAL_READ,
        ProgressStage.SENSITIVE_SCAN,
        ProgressStage.SAFE_RECONSTRUCTION,
        ProgressStage.PRIVACY_BORDER,
        ProgressStage.CLOUD_SEND,
        ProgressStage.CLOUD_REASONING,
        ProgressStage.LOCAL_VERIFY,
        ProgressStage.RETURN_RESPONSE,
    ]
    assert browser_events == terminal_events
    assert result.verification_status == "accepted"
```

- [ ] **Step 2: Add emitter calls at actual workflow boundaries**

Emit `SAFE_RECONSTRUCTION` only after the local provider returns its `DisclosureProposal`. Emit `PRIVACY_BORDER` only after `PrivacyBroker.evaluate`. Emit `CLOUD_SEND` only after an approved `ApprovedCloudPayload` exists and immediately before `CloudProvider.send`. A denied evaluation must jump from `PRIVACY_BORDER` to `RETURN_RESPONSE`.

- [ ] **Step 3: Implement the terminal presenter**

Map stages to ANSI colours only when `stream.isatty()` is true. Derive public lines from `ProgressEvent`. Print private mappings only when `TRUSTSPLIT_DEMO_PRIVATE_TRACE == "1"`; obtain them from a separate local-only callback and never attach them to `ProgressEvent`.

The border block must print:

```text
[PRIVACY BORDER] Decision: GENERALISE
[PRIVACY BORDER] Risk: 0 -> 27 | Budget cost: 9
[CLOUD PAYLOAD] {serialized broker-approved envelope}
```

- [ ] **Step 4: Add the exact-value regression test**

Create a proposal whose source text contains `18,274 TPS` and whose explicit lower-precision candidate is `15k-20k TPS`. Force generalisation, then assert the terminal cloud-payload line and provider capture contain only `15k-20k TPS`. Do not implement automatic regex-based generalisation.

- [ ] **Step 5: Run focused tests, secret verification, and lint**

Run: `cd backend && .venv/bin/pytest tests/integration/test_progress_trace.py tests/privacy/test_live_policy.py -q`

Run: `make verify-secrets`

- [ ] **Step 6: Commit**

```bash
git add backend/app/presentation/terminal.py backend/app/orchestration/state_machine.py backend/app/privacy/broker.py backend/tests
git commit -m "feat: synchronize workflow and terminal privacy trace"
```

### Task 3: Stream progress from the session API

**Files:**
- Modify: `backend/app/api/sessions.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_streaming_run.py`

**Interfaces:**
- Consumes: `DemoProgressEmitter`, `TerminalPresenter`, and `TrustSplitWorkflow.run(..., progress_emitter=...)`.
- Produces: `POST /api/sessions/{session_id}/run-stream` with `text/event-stream` records of types `progress`, `result`, and `error`.

- [ ] **Step 1: Write a failing SSE integration test**

```python
@pytest.mark.anyio
async def test_run_stream_orders_progress_before_result(client):
    session_id = await create_session(client)
    response = await client.post(
        f"/api/sessions/{session_id}/run-stream",
        json={"prompt": "Review Project Aurora"},
    )
    records = parse_sse(response.text)
    assert [record["type"] for record in records[:-1]] == ["progress"] * 8
    assert records[-1]["type"] == "result"
    assert records[-1]["data"]["verification_status"] == "accepted"
```

- [ ] **Step 2: Implement an async queue-backed stream**

Start the workflow in an `asyncio.Task`. The progress sink writes `{"type":"progress","data":event.model_dump(mode="json")}` into an `asyncio.Queue`. On completion, enqueue the serialized `WorkflowResult`; on failure, enqueue a safe error record. The response generator yields SSE frames and cancels an unfinished task in `finally`.

- [ ] **Step 3: Select timing through configuration**

Use `TRUSTSPLIT_DEMO_DELAY_SCALE`, defaulting to `1` in `scripts/dev.sh` and `0` in tests. Validate the parsed value is between `0` and `2`. Do not let request input control delays.

- [ ] **Step 4: Preserve the existing non-streaming endpoint**

Keep `POST /api/sessions/{id}/run` for compatibility and automated security probes. It uses `PresentationClock(scale=0)` and produces no theatrical delay.

- [ ] **Step 5: Run API tests and commit**

Run: `cd backend && .venv/bin/pytest tests/api/test_streaming_run.py tests/api/test_safe_api.py -q`

```bash
git add backend/app/api/sessions.py backend/app/main.py backend/tests/api/test_streaming_run.py scripts/dev.sh .env.example
git commit -m "feat: stream synchronized workflow progress"
```

### Task 4: Build the ChatGPT-style live thinking experience

**Files:**
- Create: `frontend/src/components/ThinkingTrace.tsx`
- Create: `frontend/src/stream.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/tests/thinking-trace.test.tsx`
- Test: `frontend/tests/app.test.tsx`

**Interfaces:**
- Consumes: `POST /api/sessions/{id}/run-stream` SSE contract from Task 3.
- Produces: `streamWorkflow(input, handlers)` and `ThinkingTrace({events, status})`.

- [ ] **Step 1: Write failing thinking-card tests**

```tsx
it("shows completed and active operational stages", () => {
  render(<ThinkingTrace events={[scanComplete, reconstructActive]} status="running" />);
  expect(screen.getByText("Scanning for sensitive information…")).toHaveAccessibleName(/complete/i);
  expect(screen.getByText("Reconstructing a safe prompt…")).toHaveAccessibleName(/in progress/i);
  expect(screen.queryByText(/18,274|Northstar|Oracle RAC/)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Implement the streaming client**

Use `fetch` with a POST body and incrementally parse SSE frames from `response.body.getReader()`. Call `onProgress(ProgressEvent)` for progress records and `onResult(WorkflowResult)` for the terminal result. Throw a safe `Error` for an error record or malformed terminal state.

- [ ] **Step 3: Implement the thinking card**

Render completed rows with a check icon, one active row with the existing animated cyan indicator, and hide the card after the final answer begins streaming. Respect `prefers-reduced-motion` by disabling pulsing and answer animation.

- [ ] **Step 4: Simplify the primary chat layout**

Keep the existing navigation available for judges, but make Chat the dominant default screen. Place the thinking card directly below the latest user message. Disable Send and expose Stop while streaming. Do not show raw risk calculations in the chat; retain them in Privacy Dashboard and Exposure Ledger.

- [ ] **Step 5: Stream the deterministic final answer visually**

Reveal the already-returned final answer at 25–40 characters per animation frame group, capped at 1.5 seconds total. This is presentation-only and begins only after the backend result event arrives.

- [ ] **Step 6: Run frontend checks and commit**

Run: `cd frontend && npm test && npm run typecheck && npm run lint && npm run build`

```bash
git add frontend/src frontend/tests
git commit -m "feat: add live zero-trust thinking experience"
```

### Task 5: Add the short denial demonstration and real reset

**Files:**
- Modify: `backend/app/orchestration/scenarios.py`
- Modify: `backend/app/api/demo.py`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api.ts`
- Test: `backend/tests/api/test_demo_modes.py`
- Test: `e2e/demo.spec.ts`

**Interfaces:**
- Consumes: shared progress event contract and existing synthetic exposure repository.
- Produces: a UI-selectable malicious/cumulative prompt that finishes in 6–8 seconds with `DENY`, plus confirmed `POST /api/demo/reset`.

- [ ] **Step 1: Write a failing denied-flow test**

```python
@pytest.mark.anyio
async def test_denied_stream_never_emits_cloud_send(client):
    records = await run_denial_stream(client)
    stages = [item["data"]["stage"] for item in records if item["type"] == "progress"]
    assert "privacy_border" in stages
    assert "cloud_send" not in stages
    assert records[-1]["data"]["broker_decision"]["decision"] == "deny"
```

- [ ] **Step 2: Wire the deterministic denial prompt**

Expose one clearly labelled “Try blocked request” suggestion beneath the empty composer. It uses the real broker and cumulative ledger, not a frontend-only fixture. The final chat message explains that cloud transmission was blocked and local processing remained available.

- [ ] **Step 3: Complete reset behaviour**

The reset button must call `window.confirm`, then `POST /api/demo/reset` with `{"confirmation":"RESET SYNTHETIC DEMO"}`. On success, clear conversation, progress events, selected ledger target, and session ID. On failure, retain state and show an inline error.

- [ ] **Step 4: Add browser coverage**

Playwright must assert the normal run’s eight visible stages, safe reconstructed payload, final verified answer, denial without a cloud-send stage, and successful confirmed reset. Use event arrival rather than fixed sleeps.

- [ ] **Step 5: Run tests and commit**

Run: `make test && make e2e`

```bash
git add backend/app backend/tests frontend/src e2e/demo.spec.ts
git commit -m "feat: add timed denial story and confirmed reset"
```

### Task 6: Calibrate the 3–4 minute presentation and release gate

**Files:**
- Create: `docs/demo-runbook.md`
- Modify: `README.md`
- Modify: `scripts/verify_no_secret_egress.py`
- Test: `backend/tests/integration/test_demo_timing.py`

**Interfaces:**
- Consumes: final normal and denied streamed journeys.
- Produces: repeatable presenter script and full verification evidence.

- [ ] **Step 1: Add deterministic timing assertions**

Assert the declared normal-stage delays sum to 9–11 seconds and the denial-stage delays sum to 6–8 seconds. Test declared durations without wall-clock sleeps.

- [ ] **Step 2: Strengthen the egress verifier**

Capture every approved provider payload and every safe HTTP progress/result record. Assert `Northstar`, `Oracle RAC`, `18,274`, the synthetic credential, and restricted document markers are absent. When private terminal tracing is enabled, allow markers only in the explicitly captured local terminal channel and still forbid them in provider/browser/log/database surfaces.

- [ ] **Step 3: Write the runbook**

Document a 3–4 minute sequence: 30-second framing, 60–75-second normal collaboration, 30-second terminal evidence explanation, 45–60-second denial example, and 20-second conclusion. Include the exact launcher command and prompts.

- [ ] **Step 4: Run the complete release matrix**

Run: `make test`

Run: `make build`

Run: `make verify-secrets`

Run: `make e2e`

Run: `BACKEND_PORT=18991 FRONTEND_PORT=15191 ./scripts/dev.sh --smoke`

Expected: all backend, frontend, security, browser, build, migration, and launcher checks pass. The sandboxed launcher test may skip only if the explicit out-of-sandbox smoke test passes.

- [ ] **Step 5: Perform final code review and commit documentation**

```bash
git add docs README.md scripts/verify_no_secret_egress.py backend/tests/integration/test_demo_timing.py
git commit -m "docs: add synchronized TrustSplit demo runbook"
```

Review the complete diff for secret leakage, independent UI timers, misleading AI claims, and dead demo paths before declaring the prototype complete.

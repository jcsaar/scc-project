# Synchronised Zero-Trust Chat Demo Design

## Purpose

Turn the existing TrustSplit POC into a polished, ChatGPT-style deterministic demo. The website remains focused on the conversation while a local terminal trace proves how the private prompt is transformed, checked, released, and verified. No real AI service is required.

## Demonstration Contract

- A normal run lasts 8–12 seconds; automated tests run with all delays disabled.
- The full presentation, including narration and one denial example, fits within 3–4 minutes.
- Website and terminal consume the same ordered backend progress events. They must never use independent timing scripts.
- The UI displays concise operational status, never hidden chain-of-thought.
- Private values may appear in the terminal only when `TRUSTSPLIT_DEMO_PRIVATE_TRACE=1`. They never appear in cloud payloads, API progress events, browser state, or persistent logs.
- All cloud and local-model responses are deterministic fixtures.

## User Experience

The primary screen resembles a familiar AI chat: conversation history, prompt composer, send/stop controls, and a compact provider badge. During a run, a thinking card appears beneath the prompt and advances through:

1. Reading your request locally
2. Scanning for sensitive information
3. Reconstructing a safe prompt
4. Checking the zero-trust privacy border
5. Sending approved context to Cloud AI
6. Cloud AI is reasoning
7. Verifying the response locally
8. Sending the verified response to you

Completed steps remain visible with checkmarks, the active step uses an animated indicator, and the final answer streams after verification. A denied run stops at the border and returns a safe local explanation.

## Shared Event Model

Each progress event contains `sequence`, `stage`, `public_label`, `safe_summary`, and `delay_ms`. The backend emits the event to the HTTP stream and passes the same event to the terminal presenter. Terminal-only private details are constructed separately and are never serialized into the event.

The streamed run ends with a `result` event containing the existing `WorkflowResult`. Error and cancellation events are terminal states. The existing non-streaming endpoint remains available for tests and API compatibility.

## Terminal Presentation

The terminal uses ANSI colours when attached to a TTY:

- cyan: Local AI
- yellow: safe-prompt reconstruction
- magenta: privacy border
- blue: simulated Cloud AI
- green: verified final response
- red: denied disclosure

The border trace prints the exact approved cloud payload, risk transition, privacy-budget cost, and decision. When private tracing is enabled, transformation lines such as `18,274 TPS -> 15k-20k TPS` are printed as ephemeral local demo output. The right-hand side must exactly match the approved payload.

## Failure Behaviour

- Browser disconnect cancels future presentation delays without corrupting the ledger.
- A denied disclosure produces no cloud-send event.
- A simulated cloud failure produces a local fallback result.
- Repeated submission is disabled while a run is active.
- Reset requires explicit confirmation and clears synthetic demo sessions and exposure claims.

## Acceptance Criteria

- A normal run shows all eight stages in the same order in browser and terminal.
- Stage timing totals between 8 and 12 seconds in demo mode.
- Test mode completes without real sleeps.
- The terminal cloud payload is byte-for-byte derived from the broker-approved envelope.
- Browser/network responses contain none of the protected source markers.
- The malicious/cumulative example visibly ends in `DENY` and never emits a cloud-send stage for the denied payload.
- Frontend unit tests, backend tests, secret-egress verification, production build, Playwright journeys, and launcher smoke test pass.

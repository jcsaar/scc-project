# TrustSplit AI

**Keep the secrets local. Keep the intelligence global.**

TrustSplit AI is an offline-first, chat-style proof of concept for privacy-mediated collaboration between a local model and a cloud model. **Cloud AI never directly accesses private corporate data.** Local AI understands the private context, proposes a minimum-information reconstruction, and a deterministic Privacy Broker decides whether anything may cross the boundary.

The repository contains only clearly labelled synthetic Project Aurora data. Mock local and cloud providers make the demo repeatable without internet access, Ollama, or real API credentials.

## Current POC

The browser is a focused TrustSplit chat workspace with three deterministic demo prompts:

- **Review a private architecture** — shows Local AI transforming `Northstar Financial Group`, `Oracle RAC`, and `18,274 TPS` into safe abstractions before Cloud AI reasoning.
- **Try a credential leak** — shows local detection of an API key and password, a sanitized local alternative, and a broker hard-deny with no cloud payload.
- **Try an exact customer lookup** — shows local detection of an exact name/NRIC request, a sanitized workflow alternative, and a broker hard-deny with no cloud payload.

The thinking trace is intentionally staged over roughly 11 seconds so the demo can show local reading, sensitive scanning, reconstruction, border evaluation, cloud reasoning, and local verification. The VS Code integrated terminal mirrors the public stages and prints local-only detection/reconstruction details plus the exact approved payload that crosses the border.

## Quick start

Prerequisites: Python 3.12, Node.js 20+, `uv`, and `npm`.

```bash
cd backend
uv sync --all-groups
cd ../frontend
npm ci
cd ..
make demo
```

Open `http://127.0.0.1:5173`. The API health endpoint is `http://127.0.0.1:8000/api/health`. Press `Ctrl-C` to stop both services. The backend does not hot-reload, so restart `make demo` after backend changes.

## Recommended demo flow

1. Keep the browser and VS Code terminal visible side by side.
2. Click **Review a private architecture**. Show the exact facts in the user prompt, then the safe reconstructed prompt and bounded `15k-20k TPS` cloud payload.
3. Point to the privacy receipt: `Raw facts to cloud: 0`, `Decision: ALLOW`, and `Cloud received approved context`.
4. Start a new chat and click **Try a credential leak**. Show the local safe alternative, `Transmission blocked`, and `Cloud received nothing`.
5. Repeat with **Try an exact customer lookup** to demonstrate the separate identity hard rule.
6. Close with `make verify-secrets` to demonstrate the repository egress guard.

## Technical flow

```text
Employee prompt
  → Local AI scan and reconstruction
  → Privacy Broker: ALLOW, GENERALISE, or DENY
  → approved immutable payload to Cloud AI (only when permitted)
  → local clarification and response verification
  → answer to the employee, or local fallback after a denial
```

The Privacy Broker is an application-layer semantic firewall, not a second language model. It applies deterministic hard rules for credentials and exact protected identity, then evaluates cumulative disclosure risk, precision alternatives, trust-zone budgets, and exposure-ledger evidence. Cloud adapters accept only `ApprovedCloudPayload` and have no dependency on the private repository.

## Demo modes

The primary browser experience is the mediated TrustSplit chat. Backend-only comparison modes remain available for regression tests and technical evaluation:

- **TrustSplit**: local proposal, broker policy, approved cloud reasoning, and local verification.
- **Cloud Only**: intentionally unsafe synthetic baseline; never routed to a real provider.
- **Local Only**: no egress, with reduced external reasoning utility.
- **Basic Redaction**: naive replacement baseline that leaves relational clues visible.

The backend scenario runner also covers legitimate clarification, cross-employee mosaic exposure, and malicious-cloud narrowing. These are optional technical deep-dive paths; they are not required for the primary 3–4 minute chat demo.

## Security posture

Private prompts, raw source facts, local analysis, the local oracle, and the verifier stay inside the local zone. The broker records only safe representations, semantic keys, decision reason codes, precision, heuristic risk deltas, budget costs, and audit evidence. It never persists raw private facts.

Hard rules override model recommendations. Credential values are kept in an ephemeral process-local vault and never returned to the browser, logs, prompts, or database rows. The exposure ledger is shared across employee sessions within a trust zone and isolated between providers.

See [Architecture](docs/architecture.md), [Threat model](docs/threat-model.md), [Security boundaries](docs/security-boundaries.md), and the [Demo walkthrough](docs/demo-walkthrough.md).

## Verification commands

```bash
make seed
make migrate
make test
make build
make verify-secrets
make e2e
```

`make test` runs the backend and frontend suites. `make build` compiles the backend and creates the Vite production bundle. `make e2e` runs the browser flow and expects the staged demo server to be available.

## Limitations

This is a deterministic hackathon POC, not production-ready software or a formal privacy guarantee. Responses and provider calls are simulated; the privacy mediation, policy decisions, egress envelope, ledger evidence, and local verification path are functional. The reconstruction score is an internal heuristic, not a probability. The API has no authentication or transport hardening, sessions are process-local, and policy updates are not access-controlled. See [Limitations](docs/limitations.md) for the complete list.

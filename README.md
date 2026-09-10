# TrustSplit AI

**Keep the secrets local. Keep the intelligence global.**

TrustSplit AI is an offline-first proof of concept for privacy-mediated collaboration between a local model and a cloud model. Its core invariant is: **Cloud AI never directly accesses private corporate data.** A deterministic Privacy Broker authorises the minimum useful representation, records cumulative exposure by provider trust zone, and checks every clarification request and local-oracle answer.

The repository ships only clearly labelled synthetic Project Aurora data. Mock local and cloud providers make the canonical demo repeatable without internet access, Ollama, or API credentials.

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

Open `http://127.0.0.1:5173`. The API health endpoint is `http://127.0.0.1:8000/api/health`. Press `Ctrl-C` to stop both services. After dependencies are installed, the mock-provider demo runs offline.

Useful commands:

```bash
make seed
make migrate
make test
make build
make verify-secrets
make e2e
```

## Demo modes

- **TrustSplit**: local analysis proposes a minimum-information task; the broker applies hard rules, precision controls, budget, and cumulative risk before cloud reasoning.
- **Cloud Only**: an intentionally unsafe, simulated baseline exposes the full synthetic comparison payload. It never contacts a real provider.
- **Local Only**: no data leaves the local zone, with intentionally reduced external reasoning utility.
- **Basic Redaction**: names are naively replaced, while numeric and relational clues remain visible.

The Collaboration view includes legitimate, cross-employee mosaic, and malicious-cloud narrowing stories. They are deterministic and use synthetic data.

## Security posture

Only an `ApprovedCloudPayload` can enter a real cloud adapter. The local private repository is not imported by cloud-provider modules. Hard deterministic rules override model recommendations. Provider credentials live only in a process-local expiring vault and never appear in prompts, API responses, logs, or database rows. The exposure ledger is shared across employee sessions inside one trust zone and isolated between trust zones.

See [Architecture](docs/architecture.md), [Threat model](docs/threat-model.md), [Security boundaries](docs/security-boundaries.md), and the [Demo walkthrough](docs/demo-walkthrough.md).

## Limitations

This is a hackathon POC, not production-ready software or a formal privacy guarantee. The reconstruction score is an internal heuristic, not a probability. The API has no authentication or transport hardening, sessions are process-local, and policy updates are not access-controlled. See [Limitations](docs/limitations.md) for the complete list.
# ssc-project

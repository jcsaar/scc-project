# Security boundaries

## Local Private Zone

The private prompt, synthetic source repository, raw facts, local model, oracle, and verifier stay local. Exact source data is used for analysis and verification but is never accepted by a cloud adapter.

## Privacy Broker boundary

Every cloud-bound message is created from a `DisclosureProposal` and must become an `ApprovedCloudPayload`. The broker's hard rules run before private lookup for cloud context requests. The oracle's answer crosses the broker again. Hard rules always override model recommendations.

The broker records only safe representations, semantic keys, decision reason codes, precision, heuristic risk deltas, and budget costs. It does not persist raw private facts.

## Cloud Zone

Cloud adapters receive only immutable approved disclosures and safe provider metadata. They cannot import or query the private-data repository. Provider credentials are resolved from an ephemeral server-side vault at the last responsible moment; employee credentials and company credentials are never returned to the browser.

## Trust zones and retention

Exposure is scoped to a provider trust zone and protected entity. Employees share that long-term view, so session hopping cannot erase mosaic risk. Distinct providers remain isolated. Unknown retention is conservatively treated as persistent; finite retention expires active claims without deleting audit evidence.

## Comparison-mode exception

Cloud Only and Basic Redaction intentionally display unsafe **synthetic** payloads for comparison. They use a simulated provider and are never routed through a real provider adapter. This exception does not weaken the TrustSplit path.

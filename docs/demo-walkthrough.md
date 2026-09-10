# Demo walkthrough

This **10–15 minutes** walkthrough uses only the shipped synthetic Project Aurora data.

## 1. Establish the boundary (1 minute)

Run `make demo`. In Chat, point out the Local Private Zone, the system invariant, and the synthetic-data badge. The default provider is the deterministic mock, so the demo needs no internet or credential.

## 2. Run legitimate TrustSplit collaboration (3 minutes)

Keep TrustSplit and Company Cloud selected, then choose **Run safely**. Open Privacy Pipeline. Contrast the private prompt with the exact outbound envelope: it contains a bounded `15k-20k transactions per second` representation but no exact customer, platform, project codename, internal services, or exact throughput. Open Collaboration to show that the request and oracle answer each traverse the broker before local verification.

## 3. Compare privacy and utility (2 minutes)

Run the same synthetic task in **Cloud Only**, **Local Only**, **Basic Redaction**, and **TrustSplit**:

- Cloud Only exposes the full synthetic comparison payload and reports maximum exposure.
- Local Only sends nothing and demonstrates reduced external reasoning utility.
- Basic Redaction removes names but leaves the exact numeric clue.
- TrustSplit exposes a bounded task and returns a locally verified recommendation.

## 4. Demonstrate cumulative mosaic defence (2 minutes)

In Collaboration, run **Cross-employee mosaic**. Alice and Bob receive allows, Charlie is generalised, and Dana is denied. Explain that Dana has a new session budget, but the Company Cloud exposure ledger still contains the earlier safe claims.

## 5. Demonstrate malicious narrowing (2 minutes)

Run **Malicious narrowing**. The mock cloud asks successively tighter throughput questions. Each query and answer is brokered. The cumulative heuristic rises and the final exact request is denied.

## 6. Show auditability and policy (2 minutes)

Open Privacy Dashboard for before/delta/after accounting. Open Exposure Ledger to show trust-zone scoping, then Admin / Policy to show deny thresholds and non-negotiable rules. Finish with `make verify-secrets` and state that the reconstruction score is a heuristic, not a probability.

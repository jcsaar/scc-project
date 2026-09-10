# Threat model

## Assets

Private prompts, exact customer identity, restricted source facts, internal service names, provider credentials, policy integrity, disclosure budget, and the cumulative exposure history are protected assets.

## Adversaries and failure modes

- A well-intentioned employee asks for advice that would otherwise require copying confidential context into a cloud model.
- Several employees create a **mosaic**: individually modest disclosures combine into an identifying profile.
- A **malicious** or over-curious cloud provider narrows repeated context requests to reconstruct exact values.
- A local or cloud model recommends an unsafe disclosure, returns malformed tool input, or gives advice that violates a hidden constraint.
- Logs, exception text, browser state, persistence, or credential status endpoints accidentally echo a secret.
- One provider's exposure is incorrectly reused for another provider, or the inverse: a new session incorrectly resets long-term provider memory.

## Controls

Hard rules block credentials, private keys, passwords, exact protected identity, and restricted documents. Precision ladders release the least useful detail. Risk is calculated from existing trust-zone claims plus the candidate, with synergy bonuses and deny thresholds. Request size/category/precision limits bound cloud tools. Local verification checks hidden constraints without returning source evidence. Structured logging redacts secret patterns before formatting.

## Out of scope

Compromised local operating systems, side-channel attacks, malicious repository administrators, model-weight attacks, cryptographic privacy proofs, and production identity/access management are outside this POC.

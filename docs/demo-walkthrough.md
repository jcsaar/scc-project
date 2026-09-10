# Demo walkthrough

This **3–4 minute** walkthrough uses only the shipped synthetic Project Aurora data. The browser is a familiar chat surface; the VS Code integrated terminal mirrors the technical workflow in real time.

The former **10–15 minutes** multi-view tour is intentionally condensed for a live hackathon pitch. The backend still exposes comparison modes such as **Cloud Only** for automated regression tests and follow-up experiments; the primary product path below is the mediated TrustSplit chat.

## 1. Start the local stack (20 seconds)

Run `make demo`, then open `http://127.0.0.1:5173`. The deterministic mock providers run offline. Keep the VS Code terminal visible beside the browser so the audience can see the same progress stages and the approved cloud envelope.

## 2. Run the safe path (2 minutes)

The welcome screen has three pre-made synthetic prompts so the behavior is reproducible:

- **Review a private architecture** — an approved, bounded abstraction.
- **Try a credential leak** — a synthetic API key and password that the hard rules deny.
- **Try an exact customer lookup** — a synthetic name and NRIC that the identity rule denies.

Click **Review a private architecture**. The assistant intentionally pauses for roughly 11 seconds at each realistic juncture:

1. Reading the request locally.
2. Scanning for sensitive information.
3. Reconstructing a minimum-information prompt.
4. Checking the zero-trust privacy border.
5. Sending only the immutable approved envelope to Cloud AI.
6. Verifying the cloud recommendation against hidden local constraints.
7. Returning the verified answer to the chat.

The right-hand **Live privacy receipt** makes the invariant visible: raw facts to cloud stays `0`, while the approved payload contains a bounded `15k-20k` throughput range and no exact customer, project codename, internal services, or `18,274` value. Expand **Approved payload** to show the JSON. The terminal prints the same public stages plus local-only reconstruction details and the exact payload that crossed the border.

## 3. Show a hard stop (45 seconds)

Click **New chat**, then **Try a credential leak**. The local provider proposes a credential-like disclosure. The broker rejects it before any cloud call. The receipt changes to **Transmission blocked**, the answer is a local fallback, and no secret appears in the cloud payload or browser evidence. Repeat with **Try an exact customer lookup** to show a separate hard rule for protected identity.

## 4. Close on the security story (30 seconds)

Point to the sidebar card: the private zone is active and cloud reasoning is mediated. Explain that responses are hardcoded for the hackathon, but the privacy boundary, approval decision, SSE timing, terminal trace, and egress evidence are functional. Finish with `make verify-secrets` to demonstrate the repository guard against accidental secret egress.

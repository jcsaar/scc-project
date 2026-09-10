# Limitations

TrustSplit AI is a hackathon proof of concept and is **not production-ready**.

- The reconstruction score is an internal heuristic, **not a probability**, calibrated privacy metric, or formal differential-privacy guarantee.
- The shipped data and stories are synthetic. The comparison modes are simulated and intentionally unsafe for demonstration.
- Mock model behaviour is deterministic and much narrower than real model behaviour. Real providers can be unavailable, change output formats, or produce unsafe/incorrect recommendations.
- The API has no authentication, authorisation, tenant isolation, TLS termination, CSRF protection, or production rate limiting.
- Employee provider credentials are process-local and expire or disappear on restart. The POC does not integrate an enterprise secrets manager.
- Sessions and SSE live fanout are in-memory. Audit and exposure claims persist in SQLite, but multi-process coordination and distributed transactions are not implemented.
- The policy endpoint is not protected by administrative access control, approval workflow, or signed policy bundles.
- The local repository boundary is architectural and test-enforced, not an OS sandbox or hardware enclave.
- Redaction patterns reduce accidental logging but cannot prove that arbitrary unstructured content contains no secret.
- SQLite is suitable for the local demo, not organisation-scale concurrent deployment.
- Retention behaviour is modelled at claim-selection time; secure erasure, legal holds, backup policy, and provider-side deletion guarantees are outside scope.

Before production use, add identity and access control, encrypted transport and storage, a managed secrets service, provider contractual controls, adversarial evaluation, policy governance, calibrated risk models, observability, distributed persistence, and independent security review.

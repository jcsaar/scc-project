from app.domain.disclosures import DecisionKind, DisclosureProposal, PrecisionLevel
from app.privacy.broker import PrivacyBroker


def test_broker_denies_a_proposal_containing_an_api_key() -> None:
    proposal = DisclosureProposal(
        text="Use API key sk-proj-abcdefghijklmnopqrstuvwxyz123456 to access the service.",
        purpose="Configure an integration",
        category="credential.api_key",
        requested_precision=PrecisionLevel.EXACT,
        protected_entity_ids=("project-aurora",),
        fact_keys=("provider_api_key",),
    )

    evaluation = PrivacyBroker().evaluate(proposal)

    assert evaluation.decision.decision is DecisionKind.DENY
    assert evaluation.decision.reason_code == "credential.api_key"
    assert evaluation.decision.released_text is None
    assert evaluation.approved_disclosures == ()

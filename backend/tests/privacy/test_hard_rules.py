import pytest

from app.privacy.hard_rules import DisclosureInspection, HardRuleEngine


@pytest.mark.parametrize(
    ("text", "reason_code"),
    [
        ("OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz123456", "credential.api_key"),
        ("sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456", "credential.api_key"),
        ("api_key = 'abcdefghijklmnopqrstuvwxyz1234567890'", "credential.api_key"),
        ("password: CorrectHorseBatteryStaple", "credential.password"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456", "credential.token"),
        ("-----BEGIN PRIVATE KEY-----\nabc123", "credential.private_key"),
    ],
)
def test_credentials_are_always_blocked(text: str, reason_code: str) -> None:
    result = HardRuleEngine().inspect(DisclosureInspection(text=text))

    assert result.blocked is True
    assert result.reason_code == reason_code
    assert text not in result.safe_reason


def test_exact_customer_identity_is_always_blocked() -> None:
    result = HardRuleEngine().inspect(
        DisclosureInspection(
            text="Northstar Financial Group",
            category="identity.customer",
            precision="exact",
        )
    )

    assert result.blocked is True
    assert result.reason_code == "identity.exact_customer"


def test_raw_restricted_document_is_blocked() -> None:
    result = HardRuleEngine().inspect(
        DisclosureInspection(
            text="Raw document contents",
            classification="RESTRICTED",
            is_raw_document=True,
        )
    )

    assert result.blocked is True
    assert result.reason_code == "classification.raw_restricted_document"


def test_generalised_operational_attribute_reaches_semantic_policy() -> None:
    result = HardRuleEngine().inspect(
        DisclosureInspection(
            text="A high-throughput environment",
            category="operations.throughput",
            precision="broad_category",
        )
    )

    assert result.blocked is False
    assert result.reason_code == "hard_rules.clear"

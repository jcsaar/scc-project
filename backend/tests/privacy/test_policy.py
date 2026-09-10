from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.policies import PolicyLoader

POLICY = Path(__file__).parents[3] / "policy" / "default.yaml"


def test_default_policy_defines_distinct_trust_zones() -> None:
    policy = PolicyLoader.load(POLICY)

    assert policy.trust_zones["company_cloud"].disclosure_budget == 100
    assert policy.trust_zones["personal_cloud"].disclosure_budget == 60
    assert policy.trust_zones["unapproved_cloud"].deny_at == 50
    assert policy.trust_zones["personal_cloud"].retention_days is None


def test_policy_rejects_a_deny_threshold_below_generalisation(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text(
        "max_clarification_rounds: 4\nhard_block_categories: [credential]\n"
        "trust_zones:\n  broken:\n    classification: personal\n"
        "    disclosure_budget: 60\n    retention_days: null\n"
        "    generalise_at: 75\n    deny_at: 50\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="deny_at"):
        PolicyLoader.load(invalid)

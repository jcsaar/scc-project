from pathlib import Path

import pytest

from app.private_data.repository import SyntheticPrivateRepository
from app.providers.local.mock import MockLocalModelProvider

ROOT = Path(__file__).parents[3]


@pytest.fixture
def local_provider() -> MockLocalModelProvider:
    return MockLocalModelProvider()


@pytest.fixture
def private_context():
    return SyntheticPrivateRepository(ROOT / "data" / "synthetic_project_aurora.json").load_project(
        "project-aurora"
    )


@pytest.mark.parametrize(
    ("prompt", "category", "precision"),
    [
        (
            "Use the synthetic API key sk-demo-00000000000000000000 and "
            'password="demo-aurora-123".',
            "credential",
            "exact",
        ),
        (
            "Look up the exact customer identity for Aisha Rahman, NRIC S1234567A.",
            "identity.customer",
            "exact",
        ),
    ],
)
def test_sensitive_demo_prompts_create_hard_block_candidates(
    local_provider: MockLocalModelProvider,
    private_context,
    prompt: str,
    category: str,
    precision: str,
) -> None:
    proposal = local_provider.analyse(prompt, private_context)

    assert proposal.category == category
    assert proposal.requested_precision.value == precision


def test_architecture_demo_prompt_remains_safe(
    local_provider: MockLocalModelProvider,
    private_context,
) -> None:
    proposal = local_provider.analyse(
        "Review the private transaction architecture and recommend a safe scale-out design.",
        private_context,
    )

    assert proposal.category == "architecture.contention"

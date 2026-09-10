from pathlib import Path

import pytest

from app.private_data.repository import PrivateEntityNotFound, SyntheticPrivateRepository

DATASET = Path(__file__).parents[3] / "data" / "synthetic_project_aurora.json"


def test_repository_loads_canonical_project_aurora_facts() -> None:
    repository = SyntheticPrivateRepository(DATASET)

    context = repository.load_project("project-aurora")

    assert context.synthetic_demo_data is True
    assert context.classification == "CONFIDENTIAL"
    assert repository.find_fact("project-aurora", "peak_tps").raw_value == 18_274
    assert repository.find_fact("project-aurora", "consistency_requirement").raw_value == "strong"
    partition_key = repository.find_fact("project-aurora", "natural_partition_key")
    assert partition_key.raw_value == "CustomerAccountID"


def test_unknown_project_raises_safe_not_found_error() -> None:
    repository = SyntheticPrivateRepository(DATASET)

    with pytest.raises(PrivateEntityNotFound, match="unknown-project") as error:
        repository.load_project("unknown-project")

    assert "Northstar" not in str(error.value)

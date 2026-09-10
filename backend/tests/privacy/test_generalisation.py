from pathlib import Path

from app.domain.disclosures import PrecisionLevel
from app.privacy.generalisation import PrecisionLadder
from app.private_data.repository import SyntheticPrivateRepository

DATASET = Path(__file__).parents[3] / "data" / "synthetic_project_aurora.json"


def test_throughput_candidates_are_ordered_from_least_to_most_precise() -> None:
    fact = SyntheticPrivateRepository(DATASET).find_fact("project-aurora", "peak_tps")

    candidates = PrecisionLadder().candidates(fact)

    assert [candidate.precision for candidate in candidates] == [
        PrecisionLevel.BROAD_CATEGORY,
        PrecisionLevel.COARSE_RANGE,
        PrecisionLevel.BOUNDED_RANGE,
        PrecisionLevel.APPROXIMATE,
        PrecisionLevel.EXACT,
    ]
    assert candidates[0].text == "A high-throughput environment"
    assert candidates[2].text == "15k-20k TPS"
    assert candidates[-1].text == "18,274 TPS"

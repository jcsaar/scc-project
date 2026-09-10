from app.domain.disclosures import DisclosureCandidate, PrecisionLevel
from app.domain.private import SensitiveFact


class PrecisionLadder:
    _order = (
        PrecisionLevel.BOOLEAN,
        PrecisionLevel.BROAD_CATEGORY,
        PrecisionLevel.COARSE_RANGE,
        PrecisionLevel.BOUNDED_RANGE,
        PrecisionLevel.APPROXIMATE,
        PrecisionLevel.EXACT,
    )

    def candidates(self, fact: SensitiveFact) -> tuple[DisclosureCandidate, ...]:
        return tuple(
            DisclosureCandidate(
                text=str(fact.generalizations[precision.value]),
                category=fact.category,
                precision=precision,
                fact_keys=(fact.semantic_key,),
            )
            for precision in self._order
            if precision.value in fact.generalizations
        )

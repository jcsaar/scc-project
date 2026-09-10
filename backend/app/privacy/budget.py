from pydantic import Field

from app.domain.disclosures import PrecisionLevel, StrictFrozenModel


class BudgetExceeded(ValueError):
    """Raised when a disclosure exceeds the remaining session budget."""


class BudgetPolicy:
    _base_cost = {
        PrecisionLevel.BOOLEAN: 1,
        PrecisionLevel.BROAD_CATEGORY: 2,
        PrecisionLevel.COARSE_RANGE: 4,
        PrecisionLevel.BOUNDED_RANGE: 4,
        PrecisionLevel.APPROXIMATE: 7,
        PrecisionLevel.EXACT: 12,
    }

    def cost(self, precision: PrecisionLevel, disclosure_delta: int) -> int:
        if disclosure_delta == 0:
            return 0
        return self._base_cost[precision] + disclosure_delta // 10


class BudgetAccount(StrictFrozenModel):
    initial: int = Field(ge=0)
    remaining: int = Field(ge=0)

    def charge(self, cost: int) -> "BudgetAccount":
        if cost > self.remaining:
            raise BudgetExceeded("Disclosure exceeds the remaining session budget")
        return self.model_copy(update={"remaining": self.remaining - cost})

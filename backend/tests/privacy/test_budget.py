import pytest

from app.domain.disclosures import PrecisionLevel
from app.privacy.budget import BudgetAccount, BudgetExceeded, BudgetPolicy


def test_duplicate_disclosure_costs_nothing() -> None:
    assert BudgetPolicy().cost(PrecisionLevel.EXACT, disclosure_delta=0) == 0


def test_budget_cost_combines_precision_and_disclosure_delta() -> None:
    policy = BudgetPolicy()

    assert policy.cost(PrecisionLevel.BOOLEAN, disclosure_delta=4) == 1
    assert policy.cost(PrecisionLevel.BOUNDED_RANGE, disclosure_delta=25) == 6


def test_budget_account_is_immutable_and_rejects_overspend() -> None:
    account = BudgetAccount(initial=10, remaining=10)

    updated = account.charge(4)

    assert account.remaining == 10
    assert updated.remaining == 6
    with pytest.raises(BudgetExceeded):
        updated.charge(7)

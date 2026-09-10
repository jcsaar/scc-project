from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DecisionKind(StrEnum):
    ALLOW = "allow"
    GENERALISE = "generalise"
    DENY = "deny"
    LOCAL_ONLY = "local_only"


class PrecisionLevel(StrEnum):
    BOOLEAN = "boolean"
    BROAD_CATEGORY = "broad_category"
    COARSE_RANGE = "coarse_range"
    BOUNDED_RANGE = "bounded_range"
    APPROXIMATE = "approximate"
    EXACT = "exact"


class DisclosureProposal(StrictFrozenModel):
    text: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    category: str = Field(min_length=1)
    requested_precision: PrecisionLevel
    protected_entity_ids: tuple[str, ...] = Field(min_length=1)
    fact_keys: tuple[str, ...] = Field(min_length=1)


class DisclosureCandidate(StrictFrozenModel):
    text: str = Field(min_length=1)
    category: str = Field(min_length=1)
    precision: PrecisionLevel
    fact_keys: tuple[str, ...] = Field(min_length=1)


class ApprovedDisclosure(StrictFrozenModel):
    decision_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    category: str = Field(min_length=1)
    precision: PrecisionLevel
    fact_keys: tuple[str, ...] = Field(min_length=1)


class BrokerDecision(StrictFrozenModel):
    id: str = Field(min_length=1)
    decision: DecisionKind
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    released_text: str | None = None
    released_precision: PrecisionLevel | None = None
    risk_before: int = Field(ge=0, le=100)
    risk_after: int = Field(ge=0, le=100)
    disclosure_delta: int = Field(ge=0, le=100)
    budget_cost: int = Field(ge=0)

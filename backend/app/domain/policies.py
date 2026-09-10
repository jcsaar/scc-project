from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import Field, model_validator

from app.domain.disclosures import StrictFrozenModel


class TrustZonePolicy(StrictFrozenModel):
    classification: Literal["approved", "personal", "unapproved"]
    disclosure_budget: int = Field(ge=0)
    retention_days: int | None = Field(default=None, ge=0)
    generalise_at: int = Field(ge=0, le=100)
    deny_at: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> Self:
        if self.deny_at <= self.generalise_at:
            raise ValueError("deny_at must be greater than generalise_at")
        return self


class Policy(StrictFrozenModel):
    max_clarification_rounds: int = Field(ge=1, le=10)
    hard_block_categories: tuple[str, ...]
    trust_zones: dict[str, TrustZonePolicy]


class PolicyLoader:
    @staticmethod
    def load(path: Path) -> Policy:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Policy.model_validate(document)

from pydantic import Field, JsonValue

from app.domain.disclosures import StrictFrozenModel


class SensitiveFact(StrictFrozenModel):
    semantic_key: str = Field(min_length=1)
    category: str = Field(min_length=1)
    classification: str = Field(min_length=1)
    raw_value: JsonValue
    generalizations: dict[str, JsonValue]


class PrivateContext(StrictFrozenModel):
    project_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    classification: str = Field(min_length=1)
    synthetic_demo_data: bool
    facts: tuple[SensitiveFact, ...] = Field(min_length=1)

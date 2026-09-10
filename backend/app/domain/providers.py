from pydantic import Field

from app.domain.disclosures import ApprovedDisclosure, PrecisionLevel, StrictFrozenModel


class ApprovedCloudPayload(StrictFrozenModel):
    provider_name: str = Field(min_length=1)
    trust_zone_id: str = Field(min_length=1)
    disclosures: tuple[ApprovedDisclosure, ...] = Field(min_length=1)


class CloudContextRequest(StrictFrozenModel):
    question: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    category: str = Field(min_length=1)
    requested_precision: PrecisionLevel


class CloudRecommendation(StrictFrozenModel):
    text: str = Field(min_length=1)
    context_requests: tuple[CloudContextRequest, ...] = ()

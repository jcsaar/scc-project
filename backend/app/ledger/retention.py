from datetime import datetime

from app.domain.disclosures import StrictFrozenModel


class TimedExposureClaim(StrictFrozenModel):
    semantic_key: str
    active_until: datetime | None = None


def active_claims_at(
    claims: tuple[TimedExposureClaim, ...], instant: datetime
) -> tuple[TimedExposureClaim, ...]:
    return tuple(
        claim for claim in claims if claim.active_until is None or claim.active_until > instant
    )

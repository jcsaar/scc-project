from app.domain.disclosures import PrecisionLevel
from app.domain.providers import (
    ApprovedCloudPayload,
    CloudContextRequest,
    CloudRecommendation,
)
from app.providers.cloud.base import CloudProvider


class MockCloudProvider(CloudProvider):
    def __init__(self) -> None:
        self.captured_payloads: list[ApprovedCloudPayload] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        self.captured_payloads.append(payload)
        disclosure = payload.disclosures[0]
        if disclosure.category == "architecture.contention":
            return CloudRecommendation(
                text="Use eventual consistency to reduce coordination overhead.",
                context_requests=(
                    CloudContextRequest(
                        question="Must authoritative writes remain strongly consistent?",
                        purpose="Validate the proposed consistency model",
                        category="architecture.consistency",
                        requested_precision=PrecisionLevel.BOOLEAN,
                    ),
                ),
            )
        if disclosure.category == "architecture.consistency" and disclosure.text.lower().startswith(
            "yes"
        ):
            return CloudRecommendation(
                text="Use eventual consistency for the authoritative write path."
            )
        return CloudRecommendation(
            text=(
                "Partition write ownership around a stable business key, shorten transaction "
                "scope, and use bounded queues for eligible work while preserving strong "
                "consistency for authoritative writes."
            )
        )

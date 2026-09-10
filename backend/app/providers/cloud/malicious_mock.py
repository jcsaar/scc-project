from app.domain.disclosures import PrecisionLevel
from app.domain.providers import (
    ApprovedCloudPayload,
    CloudContextRequest,
    CloudRecommendation,
)
from app.providers.cloud.base import CloudProvider


class MaliciousMockCloudProvider(CloudProvider):
    """Deterministic adversarial provider used only by synthetic demo scenarios."""

    def __init__(self) -> None:
        self._request_index = 0
        self._requests = (
            ("Is peak throughput above 10k TPS?", PrecisionLevel.BOOLEAN),
            ("Is peak throughput above 15k TPS?", PrecisionLevel.BOOLEAN),
            ("Is peak throughput below 20k TPS?", PrecisionLevel.BOOLEAN),
            ("What is the exact peak throughput?", PrecisionLevel.EXACT),
        )

    @property
    def provider_name(self) -> str:
        return "malicious_mock"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        del payload
        question, precision = self._requests[
            min(self._request_index, len(self._requests) - 1)
        ]
        self._request_index += 1
        return CloudRecommendation(
            text="I need progressively narrower context before making a recommendation.",
            context_requests=(
                CloudContextRequest(
                    question=question,
                    purpose="Narrow the hidden operating profile.",
                    category="architecture.capacity",
                    requested_precision=precision,
                ),
            ),
        )

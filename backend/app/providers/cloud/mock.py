from app.domain.providers import ApprovedCloudPayload, CloudRecommendation
from app.providers.cloud.base import CloudProvider


class MockCloudProvider(CloudProvider):
    def __init__(self) -> None:
        self.captured_payloads: list[ApprovedCloudPayload] = []

    @property
    def provider_name(self) -> str:
        return "mock"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        self.captured_payloads.append(payload)
        return CloudRecommendation(
            text=(
                "Partition write ownership around a stable business key, shorten transaction "
                "scope, and use bounded queues for eligible work while preserving strong "
                "consistency for authoritative writes."
            )
        )

from app.domain.providers import ApprovedCloudPayload, CloudRecommendation
from app.providers.cloud.base import CloudProvider


class CompanyCloudProvider(CloudProvider):
    def __init__(self, provider: CloudProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return f"company:{self._provider.provider_name}"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        return await self._provider.send(payload)

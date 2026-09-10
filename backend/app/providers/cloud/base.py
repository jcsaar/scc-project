from abc import ABC, abstractmethod

from app.domain.providers import ApprovedCloudPayload, CloudRecommendation


class CloudProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        raise NotImplementedError

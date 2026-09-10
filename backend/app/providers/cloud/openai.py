from typing import Any

from pydantic import SecretStr

from app.domain.providers import ApprovedCloudPayload, CloudRecommendation
from app.providers.cloud.base import CloudProvider


class OpenAIProvider(CloudProvider):
    def __init__(self, api_key: SecretStr, model: str, client: Any | None = None) -> None:
        if client is None:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key.get_secret_value())
        self._client = client
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        approved_text = "\n\n".join(item.text for item in payload.disclosures)
        response = await self._client.responses.create(model=self._model, input=approved_text)
        return CloudRecommendation(text=response.output_text)

    def __repr__(self) -> str:
        return f"OpenAIProvider(model={self._model!r})"

from typing import Any

from pydantic import SecretStr

from app.domain.providers import ApprovedCloudPayload, CloudRecommendation
from app.providers.cloud.base import CloudProvider


class AnthropicProvider(CloudProvider):
    def __init__(self, api_key: SecretStr, model: str, client: Any | None = None) -> None:
        if client is None:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key.get_secret_value())
        self._client = client
        self._model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def send(self, payload: ApprovedCloudPayload) -> CloudRecommendation:
        approved_text = "\n\n".join(item.text for item in payload.disclosures)
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2_048,
            messages=[{"role": "user", "content": approved_text}],
        )
        text = "\n".join(block.text for block in response.content if block.type == "text")
        return CloudRecommendation(text=text)

    def __repr__(self) -> str:
        return f"AnthropicProvider(model={self._model!r})"

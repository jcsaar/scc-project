import json

import httpx

from app.domain.disclosures import DisclosureProposal
from app.domain.private import PrivateContext
from app.domain.providers import CloudRecommendation
from app.domain.workflow import VerificationResult
from app.providers.local.base import LocalModelProvider
from app.providers.local.mock import MockLocalModelProvider


class OllamaLocalProvider(LocalModelProvider):
    def __init__(
        self,
        base_url: str,
        model: str,
        client: httpx.Client | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        self._model = model
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)
        self._verifier = MockLocalModelProvider()

    def is_available(self) -> bool:
        try:
            return self._client.get("/api/tags").is_success
        except httpx.HTTPError:
            return False

    def analyse(self, prompt: str, context: PrivateContext) -> DisclosureProposal:
        instruction = (
            "Create a JSON DisclosureProposal containing a semantic minimum-information task. "
            "Do not copy exact identities, codenames, service names, or exact operational values."
        )
        response = self._client.post(
            "/api/chat",
            json={
                "model": self._model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": instruction},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"prompt": prompt, "private_context": context.model_dump(mode="json")}
                        ),
                    },
                ],
            },
        )
        response.raise_for_status()
        return DisclosureProposal.model_validate_json(response.json()["message"]["content"])

    def verify(
        self, recommendation: CloudRecommendation, context: PrivateContext
    ) -> VerificationResult:
        return self._verifier.verify(recommendation, context)

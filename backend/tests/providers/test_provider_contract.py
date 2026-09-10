import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.domain.disclosures import ApprovedDisclosure, PrecisionLevel
from app.domain.providers import ApprovedCloudPayload
from app.private_data.repository import SyntheticPrivateRepository
from app.providers.cloud.anthropic import AnthropicProvider
from app.providers.cloud.company import CompanyCloudProvider
from app.providers.cloud.openai import OpenAIProvider
from app.providers.local.ollama import OllamaLocalProvider

DATASET = Path(__file__).parents[3] / "data" / "synthetic_project_aurora.json"


def approved_payload() -> ApprovedCloudPayload:
    return ApprovedCloudPayload(
        provider_name="provider",
        trust_zone_id="company_cloud",
        disclosures=(
            ApprovedDisclosure(
                decision_id="decision-1",
                text="A regulated organisation handles 15k-20k TPS.",
                category="architecture.contention",
                precision=PrecisionLevel.BOUNDED_RANGE,
                fact_keys=("peak_tps",),
            ),
        ),
    )


class FakeOpenAIResponses:
    def __init__(self) -> None:
        self.arguments = None

    async def create(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(output_text="Use partitioned write ownership.")


class FakeAnthropicMessages:
    def __init__(self) -> None:
        self.arguments = None

    async def create(self, **kwargs):
        self.arguments = kwargs
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="Shorten transactions.")])


@pytest.mark.anyio
async def test_openai_adapter_sends_only_approved_text() -> None:
    responses = FakeOpenAIResponses()
    client = SimpleNamespace(responses=responses)
    provider = OpenAIProvider(SecretStr("secret-openai-key"), "gpt-test", client=client)

    result = await provider.send(approved_payload())

    assert result.text == "Use partitioned write ownership."
    assert responses.arguments["input"] == "A regulated organisation handles 15k-20k TPS."
    assert "secret-openai-key" not in repr(provider)


@pytest.mark.anyio
async def test_anthropic_adapter_sends_only_approved_text() -> None:
    messages = FakeAnthropicMessages()
    client = SimpleNamespace(messages=messages)
    provider = AnthropicProvider(SecretStr("secret-anthropic-key"), "claude-test", client=client)

    result = await provider.send(approved_payload())

    assert result.text == "Shorten transactions."
    assert messages.arguments["messages"][0]["content"] == (
        "A regulated organisation handles 15k-20k TPS."
    )
    assert "secret-anthropic-key" not in repr(provider)


@pytest.mark.anyio
async def test_company_provider_wraps_an_approved_provider() -> None:
    responses = FakeOpenAIResponses()
    wrapped = OpenAIProvider(
        SecretStr("company-key"), "gpt-test", SimpleNamespace(responses=responses)
    )

    provider = CompanyCloudProvider(wrapped)
    result = await provider.send(approved_payload())

    assert provider.provider_name == "company:openai"
    assert result.text == "Use partitioned write ownership."


def test_ollama_adapter_checks_availability_and_parses_safe_proposal() -> None:
    proposal = {
        "text": "A regulated organisation operates at 15k-20k TPS.",
        "purpose": "Reduce contention",
        "category": "architecture.contention",
        "requested_precision": "bounded_range",
        "protected_entity_ids": ["project-aurora"],
        "fact_keys": ["peak_tps"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": []})
        return httpx.Response(200, json={"message": {"content": json.dumps(proposal)}})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama")
    provider = OllamaLocalProvider("http://ollama", "qwen-test", client=client)
    context = SyntheticPrivateRepository(DATASET).load_project("project-aurora")

    assert provider.is_available() is True
    assert provider.analyse("Reduce contention", context).text == proposal["text"]

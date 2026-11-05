import os
import types

import pytest

from app.integrations.llm.pydantic_ai_provider import PydanticAIExtractionProvider
from app.schemas.extraction import EmailExtractionResult


def _career_result() -> EmailExtractionResult:
    return EmailExtractionResult(
        is_career_related=True,
        company_name="Stripe",
        role_title="Staff Backend Engineer",
        current_stage="interviewing",
        event_type="interview_scheduled",
    )


@pytest.mark.asyncio
async def test_provider_uses_agent_output(monkeypatch):
    provider = PydanticAIExtractionProvider(api_key="test-api-key")
    expected = _career_result()
    captured: dict[str, str] = {}

    async def fake_run(prompt: str):
        captured["prompt"] = prompt
        return types.SimpleNamespace(output=expected)

    provider.agent = types.SimpleNamespace(run=fake_run)

    result = await provider.extract_email(
        sender="recruiter@stripe.com",
        recipients=["owner@relayn.local"],
        subject="Interview scheduled",
        body_plain="Let's schedule your system design round.",
    )

    assert result is expected
    assert "recruiter@stripe.com" in captured["prompt"]


@pytest.mark.asyncio
async def test_provider_does_not_mutate_environment(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    PydanticAIExtractionProvider(api_key="test-api-key")

    assert "GEMINI_API_KEY" not in os.environ


@pytest.mark.asyncio
async def test_provider_falls_back_without_api_key(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.llm.pydantic_ai_provider.settings.GEMINI_API_KEY",
        "",
    )
    provider = PydanticAIExtractionProvider()

    assert provider.agent is None

    result = await provider.extract_email(
        sender="jobs@stripe.com",
        recipients=["owner@relayn.local"],
        subject="Application received",
        body_plain="We received your application for Staff Backend Engineer.",
    )

    assert result.is_career_related is True
    assert result.company_name == "Stripe"

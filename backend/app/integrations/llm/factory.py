from app.core.config import settings
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.fixtures import DeterministicFixtureProvider
from app.integrations.llm.gemini import GeminiProvider


def get_llm_provider() -> LLMProvider:
    """Returns configured LLM provider (Gemini or Deterministic Fixtures)."""
    if settings.AI_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider()
    return DeterministicFixtureProvider()

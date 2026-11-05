from typing import Protocol
from app.schemas.extraction import EmailExtractionResult


class LLMProvider(Protocol):
    """Protocol for LLM extraction providers (Deterministic Fixtures, Google Gemini, etc.)."""

    async def extract_email(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        body_plain: str,
    ) -> EmailExtractionResult:
        ...

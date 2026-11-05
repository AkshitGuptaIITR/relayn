import json
import logging
from google import genai
from google.genai import types
from app.core.config import settings
from app.integrations.llm.fixtures import DeterministicFixtureProvider
from app.schemas.extraction import EmailExtractionResult

logger = logging.getLogger("relayn.gemini")

EXTRACTION_SYSTEM_PROMPT = """
You are an expert AI Career Relationship Agent.
Analyze the provided email and extract structured career management insights according to the JSON schema.

Rules:
1. Determine if this email is directly related to a job application, recruiter outreach, interview, technical test, offer, or rejection.
2. If it is NOT career related (e.g. newsletter, product marketing, order confirmation, spam), set is_career_related=false.
3. If it IS career related:
   - Identify company_name and clean domain.
   - Identify role_title.
   - Determine opportunity_type: 'application' (if user applied or in interview pipeline) or 'lead' (if recruiter reached out cold).
   - Determine current_stage: 'lead', 'applied', 'screening', 'assessment', 'interviewing', 'offer', 'rejected', or 'withdrawn'.
   - Extract event_type: factual communication event.
   - Extract recruiter/contact info (name, email, role).
   - Extract interview scheduled timestamps or assessment deadlines into milestones.
   - Extract any actionable follow-up task the candidate must take into follow_ups.
   - Extract exact evidence_quote from the body.
   - If the stage change or company match is ambiguous or uncertain, set requires_human_review=true and explain in review_reason.
"""


class GeminiProvider:
    """Google Gemini AI extraction adapter using structured JSON output schema."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-3.8-flash"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self.fallback = DeterministicFixtureProvider()

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("No GEMINI_API_KEY found; GeminiProvider will use fallback fixtures.")

    async def extract_email(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        body_plain: str,
    ) -> EmailExtractionResult:
        if not self.client:
            return await self.fallback.extract_email(sender, recipients, subject, body_plain)

        user_content = f"""
Sender: {sender}
Recipients: {', '.join(recipients)}
Subject: {subject}

Email Body:
{body_plain}
"""

        try:
            # Use synchronous call wrapped in async or direct genai client
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=EXTRACTION_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=EmailExtractionResult,
                    temperature=0.1,
                ),
            )

            if response.text:
                data = json.loads(response.text)
                return EmailExtractionResult(**data)
            else:
                logger.warning("Empty response from Gemini; falling back to fixture extractor.")
                return await self.fallback.extract_email(sender, recipients, subject, body_plain)

        except Exception as e:
            logger.exception("Gemini extraction error: %s; falling back to deterministic fixture.", e)
            return await self.fallback.extract_email(sender, recipients, subject, body_plain)

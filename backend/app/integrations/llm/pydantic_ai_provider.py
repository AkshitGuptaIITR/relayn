import logging
import os
from pydantic_ai import Agent
from app.core.config import settings
from app.integrations.llm.fixtures import DeterministicFixtureProvider
from app.schemas.extraction import EmailExtractionResult

logger = logging.getLogger("relayn.pydantic_ai")

EXTRACTION_SYSTEM_PROMPT = """
You are an expert AI Career Relationship Agent.
Analyze the provided email and extract structured career management insights according to the schema.

Rules:
1. Determine if this email is directly related to a job application, recruiter outreach, interview, technical test, offer, or rejection.
2. If it is NOT career related (e.g. newsletter, product marketing, order confirmation, spam), set is_career_related=false.
3. If it IS career related:
   - Identify company_name and clean domain.
   - Identify role_title.
   - Determine opportunity_type: 'application' or 'lead'.
   - Determine current_stage: 'lead', 'applied', 'screening', 'assessment', 'interviewing', 'offer', 'rejected', or 'withdrawn'.
   - Categorize software engineering interview rounds if applicable: 'recruiter_screen', 'technical_screen', 'coding_dsa', 'system_design', 'take_home_review', 'hiring_manager', 'behavioral', or 'onsite_loop'.
   - Extract meeting links (Google Meet, Zoom) and preparation notes into milestones.
   - Extract actionable candidate follow-up tasks into follow_ups.
   - Extract exact evidence quotes from the body.
   - If ambiguous, set requires_human_review=true and explain in review_reason.
"""


class PydanticAIExtractionProvider:
    """
    Pydantic AI agent provider for career email extraction.
    Features self-healing validation retries and provider flexibility.
    """

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.fallback = DeterministicFixtureProvider()

        if self.api_key:
            os.environ["GEMINI_API_KEY"] = self.api_key
            # Use gemini-2.5-flash or configured model
            target_model = model_name or "google:gemini-2.5-flash"
            self.agent = Agent(
                target_model,
                output_type=EmailExtractionResult,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                retries=2,
            )
        else:
            self.agent = None
            logger.warning("No GEMINI_API_KEY; PydanticAIExtractionProvider will use fallback fixtures.")

    async def extract_email(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        body_plain: str,
    ) -> EmailExtractionResult:
        if not self.agent:
            return await self.fallback.extract_email(sender, recipients, subject, body_plain)

        user_content = f"""
Sender: {sender}
Recipients: {', '.join(recipients)}
Subject: {subject}

Email Body:
{body_plain}
"""
        try:
            result = await self.agent.run(user_content)
            return result.data
        except Exception as e:
            logger.warning("Pydantic AI extraction error: %s; safely falling back to fixtures.", e)
            return await self.fallback.extract_email(sender, recipients, subject, body_plain)

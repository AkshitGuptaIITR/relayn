import json
import logging
from google import genai
from google.genai import types
from app.core.config import settings
from app.integrations.llm.fixtures import DeterministicFixtureProvider
from app.schemas.extraction import EmailExtractionResult

logger = logging.getLogger("relayn.gemini")

EXTRACTION_SYSTEM_PROMPT = """
You are an expert AI Career Relationship Intelligence Agent for software engineering professionals.
Analyze the provided email and extract structured career management insights according to the JSON schema.

### TWO-TIER CLASSIFICATION RULES:
1. primary_category:
   - "career_direct": Active personal application, interview, assessment, offer, or rejection for the candidate.
   - "career_outreach": 1-on-1 personalized recruiter or hiring manager outreach expressing interest in the candidate.
   - "career_automated": Automated job alert digests (LinkedIn, Indeed, Glassdoor), talent network newsletters, referral status updates for someone else, interview feedback surveys.
   - "non_career": Commercial marketing, order receipts, shipping notifications, newsletters, personal emails, general spam.

2. lifecycle_intent:
   - "application_acknowledgment": Confirmation that an application was submitted or received.
   - "outbound_application": Candidate sending a direct email application (e.g., attaching resume/CV or applying for a role).
   - "candidate_outreach": Candidate initiating 1-on-1 cold/warm outreach to a recruiter, HR, or hiring manager.
   - "candidate_reply": Candidate replying in an existing thread (e.g., sharing availability, confirming a slot, post-interview thank you).
   - "recruiter_screen_invitation": Recruiter reaching out or inviting candidate to schedule an initial screen.
   - "screening_scheduled": Recruiter screen date/time confirmed.
   - "technical_assessment": Take-home coding challenge, online assessment (HackerRank, CodeSignal), or repo link.
   - "interview_scheduled": Technical screen, system design, coding, or onsite loop scheduled.
   - "interview_completed": Post-interview thank you, debrief, or next step notice.
   - "interview_survey": Candidate experience feedback requests or rating surveys ("Rate your interview experience").
   - "offer_communication": Formal or informal job offer, compensation package, or offer letter.
   - "rejection_notice": Notice that the company is moving forward with other candidates.
   - "status_update": General recruitment process update, delay, or check-in.
   - "job_digest": Multi-job recommendations from aggregators, coding platform contest promos.
   - "referral_update": Updates regarding candidate referring another person.
   - "irrelevant_noise": Completely unrelated communication, receipts, alerts, shipping.

### CRITICAL BOUNDARIES & EDGE CASES:
- Non-Career Tech Company Alerts: Even if the email comes from a known tech company (e.g. GitHub, Uber, DoorDash, Stripe, Google, Apple, Amazon), if it is a delivery receipt, ride summary, monthly billing invoice, flight ticket, or technical security/vulnerability notification (e.g., "[GitHub] Security vulnerability alert"), it MUST be classified as primary_category="non_career", lifecycle_intent="irrelevant_noise", is_career_related=false.
- Referrals for Others: If the email is a candidate referral notification where the user referred someone else (e.g., "Thank you for referring [Name]"), classify as primary_category="career_automated", lifecycle_intent="referral_update", is_career_related=false.
- Candidate Experience Surveys: If the email asks to rate the interview process or provide feedback on the interview experience, classify as primary_category="career_automated", lifecycle_intent="interview_survey", is_career_related=false.
- Coding Platform Contests: If the email is from LeetCode, CodeSignal, or HackerRank announcing public contests, rankings, or courses (and NOT a specific company assessment link), classify as primary_category="career_automated", lifecycle_intent="job_digest", is_career_related=false.
- If primary_category is "career_automated" or "non_career", set is_career_related=false.
- If primary_category is "career_direct" or "career_outreach", set is_career_related=true.
- DO NOT invent a generic role title like "Software Engineer" if the role is not stated in the email. Set role_title=null, set confidence=0.7, and flag requires_human_review=true with review_reason="Role title not specified in email".
- For Software Engineering interview rounds, classify round_category:
  * "recruiter_screen": Phone screen with recruiter/talent partner.
  * "technical_screen": Initial technical phone or video screen.
  * "coding_dsa": Live coding, algorithms, data structures.
  * "system_design": Systems architecture, scalability, distributed systems.
  * "take_home_review": Review or presentation of candidate's take-home project.
  * "hiring_manager": Conversation with Engineering Director or Manager.
  * "behavioral": Values, culture fit, STAR method discussion.
  * "onsite_loop": Full interview loop or multiple rounds.
- Extract video meeting links (Google Meet, Zoom, Teams, Chime) into milestones.
- Extract preparation notes into milestones.prep_notes.
- Extract candidate action items (e.g. "Reply with availability", "Submit code by Sunday") into follow_ups.
- Extract exact supporting quote into evidence_quote.

### OUTBOUND EMAIL RULES (When Direction is OUTBOUND):
- The Sender is the candidate; the Recipients are external contacts (HR, recruiter, hiring manager).
- NEVER extract the Sender (the candidate) into contacts. Extract the relevant external Recipient(s) into contacts instead, and infer company_name/company_domain from the recipient's email domain or the email body/subject.
- Cold/warm outreach to HR or a hiring manager: primary_category="career_outreach", lifecycle_intent="candidate_outreach", opportunity_type="lead", current_stage="lead", event_type="candidate_outreach_sent", is_career_related=true.
- Direct email application (e.g., applying for a role with resume/CV): primary_category="career_direct", lifecycle_intent="outbound_application", opportunity_type="application", current_stage="applied", event_type="application_submitted", is_career_related=true.
- Routine reply in an ongoing thread (e.g., confirming interview availability, answering a recruiter question): primary_category="career_direct", lifecycle_intent="candidate_reply", current_stage=null, event_type="candidate_reply_sent", is_career_related=true.
- Personal, billing, or unrelated sent emails: primary_category="non_career", lifecycle_intent="irrelevant_noise", is_career_related=false.
"""


class GeminiProvider:
    """Google Gemini AI extraction adapter using structured JSON output schema."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
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
        direction: str = "inbound",
    ) -> EmailExtractionResult:
        if not self.client:
            return await self.fallback.extract_email(sender, recipients, subject, body_plain, direction=direction)

        user_content = f"""
Direction: {direction.upper()}
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

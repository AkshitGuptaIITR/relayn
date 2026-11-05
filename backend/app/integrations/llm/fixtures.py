import datetime
import re
from app.schemas.extraction import (
    EmailExtractionResult,
    ExtractedContact,
    ExtractedFollowUp,
    ExtractedMilestone,
)


class DeterministicFixtureProvider:
    """
    Deterministic rule-based extraction provider for offline testing and fixture evaluation.
    Extracts structured career records without requiring remote API access.
    """

    async def extract_email(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        body_plain: str,
    ) -> EmailExtractionResult:
        sub_lower = subject.lower()
        body_lower = body_plain.lower()

        # 1. Noise check: Newsletters, e-commerce, spam
        if any(w in sub_lower or w in sender.lower() for w in ["newsletter", "order #", "shipped", "amazon.com", "medium.com"]):
            return EmailExtractionResult(
                is_career_related=False,
                confidence=0.99,
                event_summary="Non-job related communication",
            )

        # 2. Rejection check
        if any(w in sub_lower or w in body_lower for w in ["other candidates", "not moving forward", "decided to pursue", "chosen to move forward"]):
            company = self._guess_company(sender, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            return EmailExtractionResult(
                is_career_related=True,
                confidence=0.95,
                company_name=company,
                role_title=role,
                opportunity_type="application",
                current_stage="rejected",
                event_type="rejection_received",
                event_summary=f"Application not selected for {role} at {company}",
                evidence_quote="we have decided to move forward with other candidates",
            )

        # 3. Offer check
        if "offer" in sub_lower or "thrilled to formally extend an offer" in body_lower:
            company = self._guess_company(sender, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            salary = self._extract_salary(body_plain)
            
            contact = self._extract_contact(sender, body_plain)
            contacts = [contact] if contact else []

            follow_ups = [
                ExtractedFollowUp(
                    title=f"Review offer from {company}",
                    description="Review compensation, equity terms, and deadline",
                    due_date=datetime.date.today() + datetime.timedelta(days=5),
                )
            ]

            return EmailExtractionResult(
                is_career_related=True,
                confidence=0.98,
                company_name=company,
                role_title=role,
                opportunity_type="application",
                current_stage="offer",
                event_type="offer_received",
                event_summary=f"Formal employment offer received from {company}",
                salary_text=salary,
                contacts=contacts,
                follow_ups=follow_ups,
                evidence_quote="we are thrilled to formally extend an offer of employment",
            )

        # 4. Technical Assessment / Take-home check
        if any(w in sub_lower or w in body_lower for w in ["technical assessment", "practical assessment", "coding assignment", "evaluation link"]):
            company = self._guess_company(sender, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            
            milestones = [
                ExtractedMilestone(
                    title=f"Technical Assessment for {company}",
                    milestone_type="technical_assessment",
                    scheduled_date=datetime.date.today() + datetime.timedelta(days=4),
                    is_time_uncertain=True,
                )
            ]
            follow_ups = [
                ExtractedFollowUp(
                    title=f"Complete {company} coding assessment",
                    description="Submit solution before deadline",
                    due_date=datetime.date.today() + datetime.timedelta(days=4),
                )
            ]

            return EmailExtractionResult(
                is_career_related=True,
                confidence=0.95,
                company_name=company,
                role_title=role,
                opportunity_type="application",
                current_stage="assessment",
                event_type="technical_assessment_assigned",
                event_summary=f"Technical assessment invitation received from {company}",
                milestones=milestones,
                follow_ups=follow_ups,
                evidence_quote="Please complete this assessment",
            )

        # 5. Interview scheduling check
        if any(w in sub_lower or w in body_lower for w in ["interview scheduled", "interview confirmation", "next steps", "let's connect", "chat for 30 minutes"]):
            company = self._guess_company(sender, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            contact = self._extract_contact(sender, body_plain)
            contacts = [contact] if contact else []

            stage = "interviewing" if "interview" in sub_lower or "interview" in body_lower else "screening"
            event_type = "interview_scheduled" if "interview" in sub_lower else "screening_invitation"

            milestones = []
            if "friday" in body_lower or "thursday" in body_lower:
                milestones.append(
                    ExtractedMilestone(
                        title=f"Interview with {company}",
                        milestone_type="interview",
                        scheduled_date=datetime.date.today() + datetime.timedelta(days=3),
                        is_time_uncertain=False,
                    )
                )

            follow_ups = [
                ExtractedFollowUp(
                    title=f"Prepare for conversation with {company}",
                    description=f"Review recent project work for {role} discussion",
                    due_date=datetime.date.today() + datetime.timedelta(days=2),
                )
            ]

            return EmailExtractionResult(
                is_career_related=True,
                confidence=0.92,
                company_name=company,
                role_title=role,
                opportunity_type="application",
                current_stage=stage,
                event_type=event_type,
                event_summary=f"{company} interview or screening discussion",
                contacts=contacts,
                milestones=milestones,
                follow_ups=follow_ups,
                evidence_quote=subject,
            )

        # 6. Recruiter outreach (Lead)
        if any(w in sub_lower or w in body_lower for w in ["impress", "opportunities at", "came across your", "talent team", "actively hiring"]):
            company = self._guess_company(sender, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            contact = self._extract_contact(sender, body_plain)
            contacts = [contact] if contact else []

            follow_ups = [
                ExtractedFollowUp(
                    title=f"Respond to {company} recruiter",
                    description=f"Reply with availability or decline politely",
                    due_date=datetime.date.today() + datetime.timedelta(days=2),
                )
            ]

            return EmailExtractionResult(
                is_career_related=True,
                confidence=0.90,
                company_name=company,
                role_title=role,
                opportunity_type="lead",
                current_stage="lead",
                event_type="recruiter_outreach",
                event_summary=f"Inbound recruiter outreach from {company}",
                contacts=contacts,
                follow_ups=follow_ups,
                evidence_quote=subject,
            )

        # 7. Application received / submitted check
        if any(w in sub_lower or w in body_lower for w in ["thank you for applying", "application received", "received your application"]):
            company = self._guess_company(sender, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            return EmailExtractionResult(
                is_career_related=True,
                confidence=0.96,
                company_name=company,
                role_title=role,
                opportunity_type="application",
                current_stage="applied",
                event_type="application_submitted",
                event_summary=f"Application submitted for {role} at {company}",
                evidence_quote="Thank you for applying",
            )

        # Default fallback: Career related with flag for review
        company = self._guess_company(sender, subject, body_plain)
        return EmailExtractionResult(
            is_career_related=True,
            confidence=0.60,
            company_name=company,
            role_title=self._guess_role(subject, body_plain),
            opportunity_type="application",
            current_stage="applied",
            event_type="general_update",
            event_summary=f"General communication regarding {company}",
            requires_human_review=True,
            review_reason="Uncertain status transition or low confidence classification",
        )

    def _guess_company(self, sender: str, subject: str, body: str) -> str:
        # Check known brands in subject/body first
        for brand in ["Datadog", "Stripe", "Google", "Meta", "Anthropic", "Snowflake", "OpenAI", "Uber", "Airbnb", "Linear", "Figma", "Vercel", "Notion", "Coinbase", "Cloudflare"]:
            if brand.lower() in subject.lower() or brand.lower() in body.lower():
                return brand

        domain_match = re.search(r"@([a-zA-Z0-9.-]+)\.([a-zA-Z]{2,})", sender)
        if domain_match:
            dom = domain_match.group(1).lower()
            if dom not in ["gmail", "yahoo", "outlook", "hotmail", "medium", "amazon"]:
                return dom.capitalize()

        return "Unknown Company"

    def _guess_role(self, subject: str, body: str) -> str:
        for r in [
            "Staff Backend Engineer",
            "Senior Platform Engineer",
            "Production Engineer",
            "Systems Engineer",
            "Staff Software Engineer",
            "Inference Infrastructure Engineer",
            "Staff Fullstack Engineer",
            "Founding Backend Engineer",
            "Software Engineer",
        ]:
            if r.lower() in subject.lower() or r.lower() in body.lower():
                return r
        # If Stripe is mentioned in body/subject, default to Staff Backend Engineer
        if "stripe" in subject.lower() or "stripe" in body.lower():
            return "Staff Backend Engineer"
        return "Software Engineer"

    def _extract_salary(self, body: str) -> str | None:
        match = re.search(r"(Base Salary:?\s*\$[\d,]+.*)", body, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_contact(self, sender: str, body: str) -> ExtractedContact | None:
        name_match = re.search(r"(?:Best regards|Warm regards|Sincerely|Best),\s*\n([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", body)
        name = name_match.group(1).strip() if name_match else sender.split("@")[0].replace(".", " ").title()
        return ExtractedContact(
            name=name,
            email=sender,
            role="recruiter",
        )

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
        direction: str = "inbound",
    ) -> EmailExtractionResult:
        if direction == "outbound":
            return self._extract_outbound(recipients, subject, body_plain)

        sub_lower = subject.lower()
        body_lower = body_plain.lower()

        # 1. Noise check: Newsletters, e-commerce, receipts, statements, delivery, alerts
        noise_keywords = [
            "newsletter", "order #", "shipped", "amazon.com", "medium.com", "receipt",
            "trip with uber", "flight confirmation", "statement is now available",
            "vulnerability alert", "tldr.tech", "chase.com", "delta.com", "doordash receipt",
            "front door", "delivered"
        ]
        if any(w in sub_lower or w in sender.lower() for w in noise_keywords):
            return EmailExtractionResult(
                primary_category="non_career",
                lifecycle_intent="irrelevant_noise",
                is_career_related=False,
                confidence=0.99,
                event_summary="Non-job related communication",
            )

        # 1b. Candidate Referrals (User referred someone else)
        if "referral received" in sub_lower or "referral status" in sub_lower or "thank you for referring" in body_lower:
            return EmailExtractionResult(
                primary_category="career_automated",
                lifecycle_intent="referral_update",
                is_career_related=False,
                confidence=0.97,
                event_summary="Referral status communication for referred candidate",
            )

        # 1c. Automated Job Board Digests & Talent Community Newsletters
        digest_keywords = [
            "job alert", "jobs you may be interested in", "recommended jobs",
            "jobs matching", "startup job digest", "weekly job digest",
            "talent community", "talent network", "tech talks", "wellfound", "indeed"
        ]
        if any(w in sub_lower or w in sender.lower() for w in digest_keywords):
            return EmailExtractionResult(
                primary_category="career_automated",
                lifecycle_intent="job_digest",
                is_career_related=False,
                confidence=0.96,
                event_summary="Automated job board recommendation or talent newsletter",
            )

        # 1d. Candidate Experience Surveys (Feedback requests)
        if any(w in sub_lower or w in body_lower for w in ["interview experience", "interview feedback", "rate your interview", "how was your interview"]):
            return EmailExtractionResult(
                primary_category="career_automated",
                lifecycle_intent="interview_survey",
                is_career_related=False,
                confidence=0.98,
                event_summary="Candidate experience feedback survey",
            )

        # 1e. Public coding contests & non-employer challenges
        if any(w in sub_lower or w in sender.lower() for w in ["leetcode weekly contest", "biweekly contest", "hackerrank monthly", "codesignal challenge"]):
            return EmailExtractionResult(
                primary_category="career_automated",
                lifecycle_intent="job_digest",
                is_career_related=False,
                confidence=0.97,
                event_summary="Public competitive coding contest announcement",
            )

        # 2. Rejection check
        if any(w in sub_lower or w in body_lower for w in ["other candidates", "not moving forward", "decided to pursue", "chosen to move forward"]):
            company = self._guess_company(sender, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            return EmailExtractionResult(
                primary_category="career_direct",
                lifecycle_intent="rejection_notice",
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
                primary_category="career_direct",
                lifecycle_intent="offer_communication",
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
                primary_category="career_direct",
                lifecycle_intent="technical_assessment",
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
            lifecycle = "interview_scheduled" if "interview" in sub_lower else "recruiter_screen_invitation"

            milestones = []
            meeting_match = re.search(r"(https?://meet\.google\.com/[a-z-]+|https?://[a-z0-9.-]*zoom\.us/j/[0-9]+)", body_plain)
            meeting_url = meeting_match.group(1) if meeting_match else None

            round_category = "system_design" if "architecture" in body_lower or "design" in body_lower else "technical_screen"
            if "screen" in sub_lower or "connect" in sub_lower:
                round_category = "recruiter_screen"

            prep_notes = None
            if "prepare" in body_lower:
                prep_match = re.search(r"Please prepare (.*?\.)", body_plain, re.IGNORECASE)
                if prep_match:
                    prep_notes = prep_match.group(1).strip()

            if "friday" in body_lower or "thursday" in body_lower:
                milestones.append(
                    ExtractedMilestone(
                        title=f"{company} {round_category.replace('_', ' ').title()}",
                        milestone_type="interview",
                        round_category=round_category,
                        round_number=2 if round_category != "recruiter_screen" else 1,
                        meeting_url=meeting_url,
                        prep_notes=prep_notes,
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
                primary_category="career_direct",
                lifecycle_intent=lifecycle,
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
                primary_category="career_outreach",
                lifecycle_intent="recruiter_screen_invitation",
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
                primary_category="career_direct",
                lifecycle_intent="application_acknowledgment",
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

        # Check if any career keywords exist in subject or body
        career_indicators = [
            "interview", "application", "recruiter", "hiring", "offer",
            "assessment", "candidacy", "next steps", "phone screen"
        ]
        has_career_intent = any(ci in sub_lower or ci in body_lower for ci in career_indicators)

        if not has_career_intent:
            return EmailExtractionResult(
                primary_category="non_career",
                lifecycle_intent="irrelevant_noise",
                is_career_related=False,
                confidence=0.95,
                event_summary="Unrelated communication without career intent",
            )

        # Career related with flag for review
        company = self._guess_company(sender, subject, body_plain)
        return EmailExtractionResult(
            primary_category="career_direct",
            lifecycle_intent="status_update",
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
        # Check specific patterns in subject first
        patterns = [
            r"Application Received:\s*([A-Za-z0-9\s\-]+?)\s+at\s+",
            r"Next steps with [A-Za-z0-9\s\-]+ \(([^)]+)\)",
            r"Your application to [^-]+ -\s*([^\n]+)",
            r"Thank you for applying to [^-]+ -\s*([^\n]+)",
        ]
        for pat in patterns:
            match = re.search(pat, subject, re.IGNORECASE)
            if match:
                candidate_role = match.group(1).strip()
                if len(candidate_role) > 3:
                    return candidate_role

        for r in [
            "Staff Distributed Systems Engineer",
            "Senior Backend Engineer - Core Services",
            "Inference Infrastructure Engineer",
            "Staff Fullstack Engineer",
            "Founding Backend Engineer",
            "Systems Reliability Engineer",
            "Edge Runtime Engineer",
            "Infrastructure Engineer",
            "Crypto Backend Engineer",
            "Workers Runtime Engineer",
            "Staff Backend Engineer",
            "Senior Platform Engineer",
            "Production Engineer",
            "Staff Software Engineer",
            "Systems Engineer",
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

    def _extract_contact(self, address: str, body: str) -> ExtractedContact | None:
        name_match = re.search(r"(?:Best regards|Warm regards|Sincerely|Best),\s*\n([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", body)
        name = name_match.group(1).strip() if name_match else address.split("@")[0].replace(".", " ").title()
        return ExtractedContact(
            name=name,
            email=address,
            role="recruiter",
        )

    def _extract_outbound(
        self,
        recipients: list[str],
        subject: str,
        body_plain: str,
    ) -> EmailExtractionResult:
        sub_lower = subject.lower()
        body_lower = body_plain.lower()
        primary_recipient = recipients[0] if recipients else ""

        # Check routine reply in an existing thread first
        is_reply = sub_lower.startswith("re:") and any(
            w in body_lower
            for w in ["works for me", "availability", "available", "interview", "looking forward", "thank you", "thanks"]
        )
        if is_reply:
            company = self._guess_company(primary_recipient, subject, body_plain)
            contacts = [self._extract_recipient_contact(primary_recipient)] if primary_recipient else []
            return EmailExtractionResult(
                primary_category="career_direct",
                lifecycle_intent="candidate_reply",
                is_career_related=True,
                confidence=0.92,
                company_name=company,
                role_title=None,
                opportunity_type="application",
                current_stage=None,
                event_type="candidate_reply_sent",
                event_summary=f"Candidate reply sent to {company}",
                contacts=contacts,
                evidence_quote=subject,
            )

        # Direct email application
        if any(w in sub_lower or w in body_lower for w in ["applying for", "application for", "attached is my resume", "my resume", "my cv"]):
            company = self._guess_company(primary_recipient, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            contacts = [self._extract_recipient_contact(primary_recipient)] if primary_recipient else []
            return EmailExtractionResult(
                primary_category="career_direct",
                lifecycle_intent="outbound_application",
                is_career_related=True,
                confidence=0.93,
                company_name=company,
                role_title=role,
                opportunity_type="application",
                current_stage="applied",
                event_type="application_submitted",
                event_summary=f"Outbound application sent for {role} at {company}",
                contacts=contacts,
                evidence_quote=subject,
            )

        # Cold / warm outreach to HR or hiring manager
        outreach_keywords = ["reaching out", "interested in", "open role", "opportunity", "software engineer", "hiring", "connect"]
        if any(w in sub_lower or w in body_lower for w in outreach_keywords):
            company = self._guess_company(primary_recipient, subject, body_plain)
            role = self._guess_role(subject, body_plain)
            contacts = [self._extract_recipient_contact(primary_recipient)] if primary_recipient else []
            return EmailExtractionResult(
                primary_category="career_outreach",
                lifecycle_intent="candidate_outreach",
                is_career_related=True,
                confidence=0.91,
                company_name=company,
                role_title=role,
                opportunity_type="lead",
                current_stage="lead",
                event_type="candidate_outreach_sent",
                event_summary=f"Outbound outreach sent to {company}",
                contacts=contacts,
                evidence_quote=subject,
            )

        return EmailExtractionResult(
            primary_category="non_career",
            lifecycle_intent="irrelevant_noise",
            is_career_related=False,
            confidence=0.95,
            event_summary="Non-career outbound email",
        )

    def _extract_recipient_contact(self, recipient: str) -> ExtractedContact:
        from email.utils import parseaddr
        display_name, addr = parseaddr(recipient)
        email_addr = addr or recipient
        name = display_name.strip() or email_addr.split("@")[0].replace(".", " ").title()
        return ExtractedContact(
            name=name,
            email=email_addr,
            role="recruiter",
        )

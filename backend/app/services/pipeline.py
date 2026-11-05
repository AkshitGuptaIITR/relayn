import logging
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory
from app.integrations.llm.base import LLMProvider
from app.integrations.llm.factory import get_llm_provider
from app.models.career import (
    Company,
    Contact,
    FollowUpTask,
    Milestone,
    Opportunity,
    OpportunityContact,
    OpportunityEvent,
    ReviewProposal,
)
from app.models.mailbox import EmailMessage
from app.schemas.extraction import EmailExtractionResult

logger = logging.getLogger("relayn.pipeline")

# Stage ranking to prevent older emails from reverting newer statuses
STAGE_RANK = {
    "lead": 1,
    "applied": 2,
    "screening": 3,
    "assessment": 4,
    "interviewing": 5,
    "offer": 6,
    "rejected": 7,
    "withdrawn": 7,
}


class CareerPipelineService:
    """
    Transforms extracted email insights into normalized relational career entities:
    - Normalizes companies and recruiter contacts
    - Matches related emails to the same ongoing Opportunity
    - Advances status monotonically and creates timeline events
    - Creates interview milestones and actionable follow-ups
    - Creates human review proposals when ambiguity is detected
    """

    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm = llm_provider or get_llm_provider()

    async def process_email_message(self, email_message_id: uuid.UUID) -> bool:
        """Processes a single email message from the database."""
        async with async_session_factory() as session:
            email = await session.get(EmailMessage, email_message_id)
            if not email or email.is_processed:
                return False

            sender = email.sender
            recipients = email.recipients
            subject = email.subject
            body = email.body_plain
            sent_at = email.sent_at

        # 1. Run structured extraction
        extracted: EmailExtractionResult = await self.llm.extract_email(
            sender=sender,
            recipients=recipients,
            subject=subject,
            body_plain=body,
        )

        async with async_session_factory() as session:
            # Re-fetch email in session to mark processed
            email = await session.get(EmailMessage, email_message_id)
            if not email:
                return False

            email.is_processed = True
            email.is_relevant = extracted.is_career_related

            if not extracted.is_career_related:
                await session.commit()
                logger.info("Email %s marked as non-career related.", email_message_id)
                return True

            # 2. Match or create Company
            company_name = extracted.company_name or "Unknown Company"
            comp_stmt = select(Company).where(Company.name.ilike(company_name))
            comp_res = await session.execute(comp_stmt)
            company = comp_res.scalar_one_or_none()

            if not company:
                company = Company(
                    name=company_name,
                    domain=extracted.company_domain,
                )
                session.add(company)
                await session.flush()

            # 3. Match or create Recruiter Contacts
            created_contacts = []
            for c_data in extracted.contacts:
                contact_stmt = select(Contact).where(Contact.email.ilike(c_data.email))
                contact_res = await session.execute(contact_stmt)
                contact = contact_res.scalar_one_or_none()

                if not contact:
                    contact = Contact(
                        company_id=company.id,
                        name=c_data.name,
                        email=c_data.email,
                        role=c_data.role,
                        linkedin_url=c_data.linkedin_url,
                    )
                    session.add(contact)
                    await session.flush()
                created_contacts.append(contact)

            # 4. Match or create Opportunity
            role_title = extracted.role_title or "Software Engineer"
            opp_stmt = (
                select(Opportunity)
                .where(Opportunity.company_id == company.id)
                .where(Opportunity.role_title.ilike(role_title))
            )
            opp_res = await session.execute(opp_stmt)
            opportunity = opp_res.scalar_one_or_none()

            is_new_opportunity = False
            if not opportunity:
                opportunity = Opportunity(
                    company_id=company.id,
                    role_title=role_title,
                    opportunity_type=extracted.opportunity_type,
                    status=extracted.current_stage or "applied",
                    provenance="inferred",
                    salary_text=extracted.salary_text,
                    location=extracted.location,
                )
                session.add(opportunity)
                await session.flush()
                is_new_opportunity = True
            else:
                # Monotonic status progression
                if extracted.current_stage:
                    curr_rank = STAGE_RANK.get(opportunity.status, 0)
                    new_rank = STAGE_RANK.get(extracted.current_stage, 0)
                    if new_rank >= curr_rank:
                        opportunity.status = extracted.current_stage
                        opportunity.record_version += 1

                if extracted.salary_text and not opportunity.salary_text:
                    opportunity.salary_text = extracted.salary_text

            # Link contacts to opportunity
            for contact in created_contacts:
                link_stmt = select(OpportunityContact).where(
                    OpportunityContact.opportunity_id == opportunity.id,
                    OpportunityContact.contact_id == contact.id,
                )
                link_res = await session.execute(link_stmt)
                if not link_res.scalar_one_or_none():
                    session.add(
                        OpportunityContact(
                            opportunity_id=opportunity.id,
                            contact_id=contact.id,
                        )
                    )

            # 5. Create Chronological OpportunityEvent
            event = OpportunityEvent(
                opportunity_id=opportunity.id,
                email_message_id=email.id,
                event_type=extracted.event_type or "general_update",
                summary=extracted.event_summary or f"Update from {company.name}",
                occurred_at=sent_at,
                provenance="inferred",
            )
            session.add(event)

            # 6. Create Milestones & SWE Interview Rounds
            for m_data in extracted.milestones:
                milestone = Milestone(
                    opportunity_id=opportunity.id,
                    title=m_data.title,
                    milestone_type=m_data.milestone_type,
                    round_category=m_data.round_category,
                    round_number=m_data.round_number,
                    meeting_url=m_data.meeting_url,
                    prep_notes=m_data.prep_notes,
                    scheduled_at=m_data.scheduled_at,
                    scheduled_date=m_data.scheduled_date,
                    is_time_uncertain=m_data.is_time_uncertain,
                    status="pending",
                )
                session.add(milestone)

            # 7. Create Follow-up Tasks
            for f_data in extracted.follow_ups:
                follow_up = FollowUpTask(
                    opportunity_id=opportunity.id,
                    title=f_data.title,
                    description=f_data.description,
                    due_date=f_data.due_date,
                    status="pending",
                )
                session.add(follow_up)

            # 8. Human Review Proposal (if flagged)
            if extracted.requires_human_review:
                proposal = ReviewProposal(
                    email_message_id=email.id,
                    opportunity_id=opportunity.id,
                    proposal_type="low_confidence_extraction",
                    proposed_changes={
                        "company_name": company_name,
                        "role_title": role_title,
                        "stage": extracted.current_stage,
                        "reason": extracted.review_reason,
                    },
                    status="pending",
                )
                session.add(proposal)

            await session.commit()
            logger.info("Successfully processed email %s into opportunity %s", email.id, opportunity.id)
            return True

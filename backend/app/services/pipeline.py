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
            email.primary_category = extracted.primary_category
            email.lifecycle_intent = extracted.lifecycle_intent
            email.classification_confidence = extracted.confidence
            email.classification_evidence = extracted.evidence_quote
            email.is_relevant = extracted.primary_category in ["career_direct", "career_outreach"]

            if not email.is_relevant:
                await session.commit()
                logger.info(
                    "Email %s categorized as %s (%s); marked non-career.",
                    email_message_id,
                    extracted.primary_category,
                    extracted.lifecycle_intent,
                )
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

            # 4. Smart Hierarchical Opportunity Resolution:
            # Step A: Match by Gmail Thread ID (Strongest signal: same email chain)
            opportunity = None
            if email.gmail_thread_id:
                thread_stmt = (
                    select(Opportunity)
                    .join(OpportunityEvent, OpportunityEvent.opportunity_id == Opportunity.id)
                    .join(EmailMessage, OpportunityEvent.email_message_id == EmailMessage.id)
                    .where(EmailMessage.gmail_thread_id == email.gmail_thread_id)
                    .limit(1)
                )
                thread_res = await session.execute(thread_stmt)
                opportunity = thread_res.scalar_one_or_none()

            # Step B: Match by Recruiter Contact already linked to an active opportunity at this company
            if not opportunity and created_contacts:
                contact_ids = [c.id for c in created_contacts]
                contact_opp_stmt = (
                    select(Opportunity)
                    .join(OpportunityContact, OpportunityContact.opportunity_id == Opportunity.id)
                    .where(OpportunityContact.contact_id.in_(contact_ids))
                    .where(Opportunity.company_id == company.id)
                    .where(Opportunity.status.notin_(["rejected", "withdrawn"]))
                    .order_by(Opportunity.updated_at.desc())
                    .limit(1)
                )
                contact_opp_res = await session.execute(contact_opp_stmt)
                opportunity = contact_opp_res.scalar_one_or_none()

            # Step C: Match by Company with exactly ONE active (non-terminal) opportunity
            if not opportunity:
                active_stmt = (
                    select(Opportunity)
                    .where(Opportunity.company_id == company.id)
                    .where(Opportunity.status.notin_(["rejected", "withdrawn"]))
                )
                active_res = await session.execute(active_stmt)
                active_opps = active_res.scalars().all()
                if len(active_opps) == 1:
                    opportunity = active_opps[0]

            # Step D: Match by Role Title (exact or substring/fuzzy) if multiple or no active
            if not opportunity and extracted.role_title:
                role_stmt = (
                    select(Opportunity)
                    .where(Opportunity.company_id == company.id)
                    .where(Opportunity.role_title.ilike(f"%{extracted.role_title}%"))
                    .order_by(Opportunity.updated_at.desc())
                    .limit(1)
                )
                role_res = await session.execute(role_stmt)
                opportunity = role_res.scalar_one_or_none()

            # Step E: Keyword overlap matching between role titles
            if not opportunity and extracted.role_title:
                all_opps_stmt = select(Opportunity).where(Opportunity.company_id == company.id)
                all_opps = (await session.execute(all_opps_stmt)).scalars().all()
                stopwords = {"engineer", "engineering", "at", "for", "the", "-", "role", "position"}
                extracted_words = {w for w in extracted.role_title.lower().split() if w not in stopwords}
                for candidate in all_opps:
                    cand_words = {w for w in candidate.role_title.lower().split() if w not in stopwords}
                    if extracted_words and cand_words and (extracted_words.issubset(cand_words) or cand_words.issubset(extracted_words)):
                        opportunity = candidate
                        break

            # Step F: Create new Opportunity if no existing candidacy matched
            is_new_opportunity = False
            role_title = extracted.role_title or "Software Engineer"
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
                # If existing opportunity had a generic title and the new email has a specific role, upgrade it
                if (
                    opportunity.role_title in ["Software Engineer", "Systems Engineer", "Unknown Role"]
                    and extracted.role_title
                    and extracted.role_title not in ["Software Engineer", "Systems Engineer"]
                ):
                    opportunity.role_title = extracted.role_title

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

            # 8. Human Review Proposal (if flagged or low confidence or missing role)
            should_review = (
                extracted.requires_human_review
                or extracted.confidence < 0.80
                or extracted.role_title is None
            )
            if should_review:
                proposal_type = (
                    "low_confidence_extraction"
                    if extracted.confidence < 0.80
                    else "ambiguous_role_or_match"
                )
                proposal = ReviewProposal(
                    email_message_id=email.id,
                    opportunity_id=opportunity.id,
                    proposal_type=proposal_type,
                    proposed_changes={
                        "company_name": company_name,
                        "role_title": opportunity.role_title,
                        "stage": extracted.current_stage,
                        "confidence": extracted.confidence,
                        "reason": extracted.review_reason or "Low confidence or missing role title",
                    },
                    status="pending",
                )
                session.add(proposal)

            await session.commit()
            logger.info("Successfully processed email %s into opportunity %s", email.id, opportunity.id)
            return True

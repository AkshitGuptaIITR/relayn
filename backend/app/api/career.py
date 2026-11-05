import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_authenticated_owner
from app.db.session import get_db_session
from app.models.career import (
    Company,
    Contact,
    FollowUpTask,
    Milestone,
    Opportunity,
    OpportunityEvent,
    ReviewProposal,
)
from app.schemas.career import (
    ContactDTO,
    FollowUpTaskDTO,
    MilestoneDTO,
    OpportunityDetailDTO,
    OpportunityEventDTO,
    OpportunitySummaryDTO,
    ReviewProposalDTO,
)

router = APIRouter(prefix="/api/career", tags=["career"])


@router.get("/opportunities", response_model=list[OpportunitySummaryDTO])
async def list_opportunities(
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Returns list of opportunities with company and latest activity."""
    stmt = (
        select(Opportunity)
        .options(selectinload(Opportunity.company), selectinload(Opportunity.follow_ups), selectinload(Opportunity.milestones))
        .order_by(Opportunity.updated_at.desc())
    )

    if status_filter:
        stmt = stmt.where(Opportunity.status == status_filter)
    if type_filter:
        stmt = stmt.where(Opportunity.opportunity_type == type_filter)

    result = await db.execute(stmt)
    opps = result.scalars().all()

    summaries = []
    for opp in opps:
        pending_tasks = len([f for f in opp.follow_ups if f.status == "pending"])
        interviews = len([m for m in opp.milestones if m.status == "pending" and m.milestone_type == "interview"])
        summaries.append(
            OpportunitySummaryDTO(
                id=opp.id,
                company_name=opp.company.name,
                company_domain=opp.company.domain,
                role_title=opp.role_title,
                opportunity_type=opp.opportunity_type,
                status=opp.status,
                salary_text=opp.salary_text,
                location=opp.location,
                last_activity_at=opp.updated_at,
                pending_follow_ups_count=pending_tasks,
                upcoming_interviews_count=interviews,
            )
        )
    return summaries


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetailDTO)
async def get_opportunity_detail(
    opportunity_id: uuid.UUID,
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Returns full details of an opportunity including timeline, SWE interview rounds, and tasks."""
    stmt = (
        select(Opportunity)
        .options(
            selectinload(Opportunity.company),
            selectinload(Opportunity.events),
            selectinload(Opportunity.milestones),
            selectinload(Opportunity.follow_ups),
            selectinload(Opportunity.contacts),
        )
        .where(Opportunity.id == opportunity_id)
    )
    result = await db.execute(stmt)
    opp = result.scalar_one_or_none()

    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # Fetch contacts
    contacts_stmt = (
        select(Contact)
        .join(Opportunity.contacts)
        .where(Opportunity.id == opportunity_id)
    )
    contacts_res = await db.execute(contacts_stmt)
    contacts = contacts_res.scalars().all()

    return OpportunityDetailDTO(
        id=opp.id,
        company_name=opp.company.name,
        company_domain=opp.company.domain,
        role_title=opp.role_title,
        opportunity_type=opp.opportunity_type,
        status=opp.status,
        salary_text=opp.salary_text,
        location=opp.location,
        notes=opp.notes,
        created_at=opp.created_at,
        updated_at=opp.updated_at,
        contacts=[
            ContactDTO(
                id=c.id,
                name=c.name,
                email=c.email,
                role=c.role,
                linkedin_url=c.linkedin_url,
            )
            for c in contacts
        ],
        milestones=[
            MilestoneDTO(
                id=m.id,
                title=m.title,
                milestone_type=m.milestone_type,
                round_category=m.round_category,
                round_number=m.round_number,
                meeting_url=m.meeting_url,
                prep_notes=m.prep_notes,
                scheduled_at=m.scheduled_at,
                scheduled_date=m.scheduled_date,
                is_time_uncertain=m.is_time_uncertain,
                status=m.status,
            )
            for m in opp.milestones
        ],
        follow_ups=[
            FollowUpTaskDTO(
                id=f.id,
                title=f.title,
                description=f.description,
                due_date=f.due_date,
                status=f.status,
            )
            for f in opp.follow_ups
        ],
        events=[
            OpportunityEventDTO(
                id=e.id,
                event_type=e.event_type,
                summary=e.summary,
                occurred_at=e.occurred_at,
                email_message_id=e.email_message_id,
            )
            for e in opp.events
        ],
    )


@router.post("/follow-ups/{task_id}/resolve")
async def resolve_follow_up(
    task_id: uuid.UUID,
    action: str = Query(..., pattern="^(completed|dismissed)$"),
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Mark a follow-up task as completed or dismissed."""
    task = await db.get(FollowUpTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Follow-up task not found")
    task.status = action
    await db.commit()
    return {"status": "ok", "action": action}


@router.get("/review-proposals", response_model=list[ReviewProposalDTO])
async def list_review_proposals(
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """List pending review proposals."""
    stmt = (
        select(ReviewProposal)
        .where(ReviewProposal.status == "pending")
        .order_by(ReviewProposal.created_at.desc())
    )
    res = await db.execute(stmt)
    proposals = res.scalars().all()
    return [
        ReviewProposalDTO(
            id=p.id,
            email_message_id=p.email_message_id,
            opportunity_id=p.opportunity_id,
            proposal_type=p.proposal_type,
            proposed_changes=p.proposed_changes,
            status=p.status,
            created_at=p.created_at,
        )
        for p in proposals
    ]


@router.post("/review-proposals/{proposal_id}/resolve")
async def resolve_review_proposal(
    proposal_id: uuid.UUID,
    action: str = Query(..., pattern="^(accepted|dismissed)$"),
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Resolve a review proposal."""
    proposal = await db.get(ReviewProposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal.status = action
    proposal.resolved_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return {"status": "ok", "action": action}

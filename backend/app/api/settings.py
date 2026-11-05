from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_authenticated_owner
from app.core.config import settings
from app.db.session import get_db_session
from app.jobs.repository import JobRepository
from app.models.auth import InstallationState
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
from app.models.mailbox import EmailMessage, MailboxAccount
from app.schemas.settings import (
    LifecycleActionResponse,
    SettingsResponse,
    UpdateSettingsRequest,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Returns owner preferences, timezone, and mailbox connection status."""
    state_res = await db.execute(select(InstallationState).where(InstallationState.id == 1))
    state = state_res.scalar_one_or_none()

    mb_res = await db.execute(select(MailboxAccount).limit(1))
    mailbox = mb_res.scalar_one_or_none()

    return SettingsResponse(
        timezone=state.timezone if state else settings.RELAYN_TIMEZONE,
        is_demo_mode=state.is_demo_mode if state else False,
        is_setup_completed=state.is_setup_completed if state else True,
        mailbox_email=mailbox.email_address if mailbox else None,
        sync_status=mailbox.sync_status if mailbox else "idle",
        has_google_credentials=bool(mailbox and mailbox.encrypted_credentials),
        ai_provider="pydantic-ai",
    )


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    payload: UpdateSettingsRequest,
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Updates owner preferences (timezone, demo mode toggle)."""
    state_res = await db.execute(select(InstallationState).where(InstallationState.id == 1))
    state = state_res.scalar_one_or_none()
    if not state:
        state = InstallationState(id=1)
        db.add(state)

    if payload.timezone is not None:
        state.timezone = payload.timezone
    if payload.is_demo_mode is not None:
        state.is_demo_mode = payload.is_demo_mode

    await db.commit()
    await db.refresh(state)

    mb_res = await db.execute(select(MailboxAccount).limit(1))
    mailbox = mb_res.scalar_one_or_none()

    return SettingsResponse(
        timezone=state.timezone,
        is_demo_mode=state.is_demo_mode,
        is_setup_completed=state.is_setup_completed,
        mailbox_email=mailbox.email_address if mailbox else None,
        sync_status=mailbox.sync_status if mailbox else "idle",
        has_google_credentials=bool(mailbox and mailbox.encrypted_credentials),
        ai_provider="pydantic-ai",
    )


@router.post("/disconnect", response_model=LifecycleActionResponse)
async def disconnect_mailbox(
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Disconnects Gmail mailbox:
    - Removes stored encrypted Google tokens and resets to disconnected state.
    - Preserves all imported messages, career opportunities, events, and tasks.
    """
    mb_res = await db.execute(select(MailboxAccount).limit(1))
    mailbox = mb_res.scalar_one_or_none()

    if mailbox:
        mailbox.encrypted_credentials = None
        mailbox.sync_status = "disconnected"
        mailbox.sync_error = None
        await db.commit()

    return LifecycleActionResponse(
        message="Mailbox disconnected successfully. Your existing career records remain saved.",
        status="disconnected",
    )


@router.post("/purge", response_model=LifecycleActionResponse)
async def purge_all_data(
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Full data purge:
    - Increments mailbox generation counter to fence out any in-flight background worker jobs.
    - Purges all opportunities, companies, contacts, milestones, follow-ups, and raw email messages.
    - Preserves local owner master password and app settings.
    """
    mb_res = await db.execute(select(MailboxAccount).limit(1))
    mailbox = mb_res.scalar_one_or_none()

    # 1. Generation fencing: Cancel all in-flight or queued background jobs
    new_gen = 2
    if mailbox:
        mailbox.generation += 1
        new_gen = mailbox.generation
        mailbox.last_history_id = None
        mailbox.sync_status = "idle"
        mailbox.sync_error = None

    repo = JobRepository(db)
    await repo.cancel_generation(new_gen)

    # 2. Delete all domain records cleanly
    await db.execute(delete(ReviewProposal))
    await db.execute(delete(FollowUpTask))
    await db.execute(delete(Milestone))
    await db.execute(delete(OpportunityEvent))
    await db.execute(delete(OpportunityContact))
    await db.execute(delete(Opportunity))
    await db.execute(delete(Contact))
    await db.execute(delete(Company))
    await db.execute(delete(EmailMessage))

    await db.commit()

    return LifecycleActionResponse(
        message="All career data, opportunities, and imported emails have been purged successfully.",
        status="purged",
    )

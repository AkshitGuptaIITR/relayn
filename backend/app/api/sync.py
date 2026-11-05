from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_authenticated_owner
from app.db.session import get_db_session
from app.models.jobs import Job
from app.models.mailbox import EmailMessage, MailboxAccount
from app.schemas.sync import JobStatusResponse, SyncTriggerResponse
from app.services.sync import MailboxSyncService

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/trigger", response_model=SyncTriggerResponse)
async def trigger_sync(
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Manually triggers mailbox sync and enqueues email processing jobs."""
    sync_service = MailboxSyncService()
    try:
        new_count = await sync_service.sync_mailbox(trigger="manual_trigger")
        return SyncTriggerResponse(
            message=f"Mailbox sync completed successfully. Ingested {new_count} new messages.",
            new_messages=new_count,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mailbox sync failed: {e}",
        )


@router.get("/status", response_model=JobStatusResponse)
async def get_sync_and_job_status(
    session: dict = Depends(require_authenticated_owner),
    db: AsyncSession = Depends(get_db_session),
):
    """Returns current sync status and background job queue counts."""
    # 1. Mailbox status
    mb_stmt = select(MailboxAccount).limit(1)
    mb_res = await db.execute(mb_stmt)
    mailbox = mb_res.scalar_one_or_none()

    # 2. Total messages
    msg_stmt = select(func.count(EmailMessage.id))
    msg_count = (await db.execute(msg_stmt)).scalar() or 0

    # 3. Job status counts
    jobs_stmt = select(Job.status, func.count(Job.id)).group_by(Job.status)
    jobs_res = await db.execute(jobs_stmt)
    status_counts = dict(jobs_res.fetchall())

    return JobStatusResponse(
        sync_status=mailbox.sync_status if mailbox else "idle",
        last_synced_at=mailbox.last_synced_at if mailbox else None,
        last_history_id=mailbox.last_history_id if mailbox else None,
        sync_error=mailbox.sync_error if mailbox else None,
        queued_jobs=status_counts.get("queued", 0),
        running_jobs=status_counts.get("running", 0),
        completed_jobs=status_counts.get("completed", 0),
        failed_jobs=status_counts.get("failed", 0),
        total_messages=msg_count,
    )

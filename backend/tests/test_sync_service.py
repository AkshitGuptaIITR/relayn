import pytest
from sqlalchemy import func, select
from app.db.session import async_session_factory
from app.integrations.mailbox.synthetic import SyntheticMailboxGateway
from app.models.jobs import Job
from app.models.mailbox import EmailMessage, MailboxAccount
from app.services.sync import MailboxSyncService


@pytest.mark.asyncio
async def test_synthetic_mailbox_sync_and_deduplication():
    gateway = SyntheticMailboxGateway()
    sync_service = MailboxSyncService(gateway=gateway)

    # Clean DB before test
    async with async_session_factory() as session:
        await session.execute(EmailMessage.__table__.delete())
        await session.execute(Job.__table__.delete())
        await session.execute(MailboxAccount.__table__.delete())
        await session.commit()

    # 1. Initial sync
    new_count = await sync_service.sync_mailbox(trigger="test_initial")
    assert new_count > 0

    # Verify messages and queued jobs exist in DB
    async with async_session_factory() as session:
        msg_count = (await session.execute(select(func.count(EmailMessage.id)))).scalar()
        job_count = (await session.execute(select(func.count(Job.id)).where(Job.job_type == "process_email"))).scalar()
        assert msg_count == new_count
        assert job_count == new_count

    # 2. Second sync immediately after: should ingest 0 duplicates
    second_count = await sync_service.sync_mailbox(trigger="test_incremental")
    assert second_count == 0

    # Verify message count did not change
    async with async_session_factory() as session:
        msg_count_after = (await session.execute(select(func.count(EmailMessage.id)))).scalar()
        assert msg_count_after == msg_count

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
    new_count = await sync_service.sync_mailbox(trigger="test_initial", limit=500)
    assert new_count > 0

    # Verify messages and queued jobs exist in DB
    async with async_session_factory() as session:
        msg_count = (await session.execute(select(func.count(EmailMessage.id)))).scalar()
        job_count = (await session.execute(select(func.count(Job.id)).where(Job.job_type == "process_email"))).scalar()
        assert msg_count == new_count
        assert job_count == new_count

    # 2. Second sync immediately after: should ingest 0 duplicates
    second_count = await sync_service.sync_mailbox(trigger="test_incremental", limit=500)
    assert second_count == 0

    # Verify message count did not change
    async with async_session_factory() as session:
        msg_count_after = (await session.execute(select(func.count(EmailMessage.id)))).scalar()
        assert msg_count_after == msg_count


@pytest.mark.asyncio
async def test_outbound_direction_detection_from_labels_and_sender():
    import datetime
    from app.integrations.mailbox.gateway import IngestedMessage, SyncResult

    class OutboundStubGateway:
        async def fetch_messages(self, after_history_id=None, limit=50):
            now = datetime.datetime.now(datetime.timezone.utc)
            return SyncResult(
                messages=[
                    IngestedMessage(
                        gmail_message_id="msg_sent_label",
                        gmail_thread_id="thread_sent_1",
                        history_id="2001",
                        direction="outbound",
                        label_ids=["SENT"],
                        sender="demo.owner@relayn.local",
                        recipients=["hr@acme.io"],
                        subject="Reaching out about Backend Engineer role",
                        sent_at=now,
                        body_plain="Hi, interested in open roles.",
                    ),
                    IngestedMessage(
                        gmail_message_id="msg_sent_sender_match",
                        gmail_thread_id="thread_sent_2",
                        history_id="2002",
                        direction="inbound",
                        label_ids=[],
                        sender="Owner <demo.owner@relayn.local>",
                        recipients=["jobs@beta.io"],
                        subject="Applying for Software Engineer",
                        sent_at=now,
                        body_plain="Attached is my resume.",
                    ),
                ],
                new_history_id="2002",
                has_more=False,
            )

    async with async_session_factory() as session:
        await session.execute(EmailMessage.__table__.delete())
        await session.execute(Job.__table__.delete())
        await session.execute(MailboxAccount.__table__.delete())
        await session.commit()

    sync_service = MailboxSyncService(gateway=OutboundStubGateway())
    count = await sync_service.sync_mailbox(trigger="test_outbound", limit=10)
    assert count == 2

    async with async_session_factory() as session:
        msgs = (await session.execute(select(EmailMessage).order_by(EmailMessage.history_id.asc()))).scalars().all()
        assert len(msgs) == 2
        assert msgs[0].direction == "outbound"
        assert msgs[0].label_ids == ["SENT"]
        assert msgs[1].direction == "outbound"

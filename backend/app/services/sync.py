import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory
from app.integrations.mailbox.gateway import SyncResult
from app.integrations.mailbox.synthetic import SyntheticMailboxGateway
from app.jobs.repository import JobRepository
from app.models.auth import InstallationState
from app.models.mailbox import EmailMessage, MailboxAccount

logger = logging.getLogger("relayn.sync")


class MailboxSyncService:
    """
    Orchestrates mailbox synchronization:
    1. Fetches new messages from the configured gateway (Synthetic or real Gmail).
    2. Persists newly discovered messages into email_messages (deduplicated by gmail_message_id).
    3. Enqueues a process_email job for each new message.
    4. Advances last_history_id and updates sync_status.
    """

    def __init__(self, gateway=None):
        self.gateway = gateway or SyntheticMailboxGateway()

    async def sync_mailbox(self, trigger: str = "manual") -> int:
        async with async_session_factory() as session:
            # 1. Get or create singleton MailboxAccount
            stmt = select(MailboxAccount).limit(1)
            result = await session.execute(stmt)
            mailbox = result.scalar_one_or_none()

            if not mailbox:
                mailbox = MailboxAccount(
                    email_address="demo.owner@relayn.local",
                    sync_status="idle",
                )
                session.add(mailbox)
                await session.flush()

            mailbox.sync_status = "syncing"
            mailbox.sync_error = None
            await session.commit()
            mailbox_id = mailbox.id
            last_history = mailbox.last_history_id
            generation = mailbox.generation

        try:
            # 2. Fetch messages from gateway
            sync_result: SyncResult = await self.gateway.fetch_messages(after_history_id=last_history)
            new_messages_count = 0

            async with async_session_factory() as session:
                repo = JobRepository(session)

                for msg_data in sync_result.messages:
                    # Check if already imported
                    check_stmt = select(EmailMessage).where(EmailMessage.gmail_message_id == msg_data.gmail_message_id)
                    check_res = await session.execute(check_stmt)
                    if check_res.scalar_one_or_none():
                        continue

                    # Insert raw email record
                    email_msg = EmailMessage(
                        mailbox_id=mailbox_id,
                        gmail_message_id=msg_data.gmail_message_id,
                        gmail_thread_id=msg_data.gmail_thread_id,
                        history_id=msg_data.history_id,
                        sender=msg_data.sender,
                        recipients=msg_data.recipients,
                        subject=msg_data.subject,
                        sent_at=msg_data.sent_at,
                        snippet=msg_data.snippet,
                        body_plain=msg_data.body_plain,
                        generation=generation,
                    )
                    session.add(email_msg)
                    await session.flush()

                    # Enqueue processing job for this email
                    await repo.enqueue(
                        job_type="process_email",
                        payload={"email_message_id": str(email_msg.id)},
                        unique_key=f"process_email_{email_msg.id}",
                        generation=generation,
                        priority=2,
                    )
                    new_messages_count += 1

                # 3. Update mailbox account with new cursor
                mb = await session.get(MailboxAccount, mailbox_id)
                if mb:
                    mb.sync_status = "idle"
                    if sync_result.new_history_id:
                        mb.last_history_id = sync_result.new_history_id
                    mb.last_synced_at = msg_data.sent_at if sync_result.messages else mb.last_synced_at

                await session.commit()

            logger.info("Sync finished. Ingested %d new messages.", new_messages_count)
            return new_messages_count

        except Exception as e:
            logger.exception("Mailbox sync failed: %s", e)
            async with async_session_factory() as session:
                mb = await session.get(MailboxAccount, mailbox_id)
                if mb:
                    mb.sync_status = "error"
                    mb.sync_error = str(e)
                await session.commit()
            raise

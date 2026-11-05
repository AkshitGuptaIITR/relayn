import logging
import uuid
from typing import Any
from app.services.pipeline import CareerPipelineService
from app.services.sync import MailboxSyncService

logger = logging.getLogger("relayn.handlers")


class SyncMailboxHandler:
    """Handler for 'sync_mailbox' jobs."""

    def __init__(self, sync_service: MailboxSyncService | None = None):
        self.sync_service = sync_service or MailboxSyncService()

    async def handle(self, payload: dict[str, Any]) -> None:
        trigger = payload.get("trigger", "scheduled")
        logger.info("Executing sync_mailbox job (trigger=%s)", trigger)
        await self.sync_service.sync_mailbox(trigger=trigger)


class ProcessEmailHandler:
    """Handler for 'process_email' jobs."""

    def __init__(self, pipeline_service: CareerPipelineService | None = None):
        self.pipeline_service = pipeline_service or CareerPipelineService()

    async def handle(self, payload: dict[str, Any]) -> None:
        email_id_str = payload.get("email_message_id")
        if not email_id_str:
            raise ValueError("Missing email_message_id in payload")
        email_id = uuid.UUID(email_id_str)
        await self.pipeline_service.process_email_message(email_id)

import asyncio
import logging
import signal
import sys
from typing import Any
from app.db.session import async_session_factory
from app.jobs.dispatcher import JobDispatcher
from app.jobs.handlers import ProcessEmailHandler, SyncMailboxHandler
from app.jobs.repository import JobRepository

logger = logging.getLogger("relayn.worker")


def create_default_dispatcher() -> JobDispatcher:
    """Builds and registers default job handlers for the background worker."""
    dispatcher = JobDispatcher()
    dispatcher.register("sync_mailbox", SyncMailboxHandler())
    dispatcher.register("process_email", ProcessEmailHandler())
    return dispatcher


class BackgroundWorker:
    """
    Standalone background worker:
    - Polling loop claiming queued/recoverable jobs with FOR UPDATE SKIP LOCKED
    - Independent lease heartbeat renewal task during job execution
    - Periodic scheduler for recurring mailbox sync checks
    - Graceful shutdown handling on SIGINT/SIGTERM
    """

    def __init__(
        self,
        dispatcher: JobDispatcher,
        poll_interval_seconds: float = 2.0,
        lease_duration_seconds: int = 60,
        sync_interval_seconds: int = 300,  # 5 minutes default
    ):
        self.dispatcher = dispatcher
        self.poll_interval_seconds = poll_interval_seconds
        self.lease_duration_seconds = lease_duration_seconds
        self.sync_interval_seconds = sync_interval_seconds
        self.is_running = False
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        """Signal the worker to gracefully complete in-flight tasks and exit."""
        logger.info("Worker stop requested.")
        self.is_running = False
        self._stop_event.set()

    async def run(self) -> None:
        """Main worker execution loop."""
        self.is_running = True
        self._stop_event.clear()
        logger.info("Starting Relayn Background Worker...")

        # Start periodic scheduler task
        scheduler_task = asyncio.create_task(self._scheduler_loop())

        try:
            while self.is_running:
                claimed = await self._claim_and_execute_one()
                if not claimed:
                    # No job claimed, wait poll interval or until stop signaled
                    try:
                        await asyncio.wait_for(
                            self._stop_event.wait(),
                            timeout=self.poll_interval_seconds,
                        )
                    except asyncio.TimeoutError:
                        pass
        finally:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("Relayn Background Worker stopped.")

    async def _claim_and_execute_one(self) -> bool:
        """Claims one eligible job and executes it with heartbeat protection."""
        registered_types = self.dispatcher.registered_types()
        if not registered_types:
            return False

        async with async_session_factory() as session:
            repo = JobRepository(session)
            job = await repo.claim_next_job(
                job_types=registered_types,
                lease_duration_seconds=self.lease_duration_seconds,
            )
            await session.commit()

            if not job:
                return False

            job_id = job.id
            lease_token = job.lease_token
            job_type = job.job_type
            payload = job.payload

        logger.info("Claimed job %s (type=%s, attempt=%s)", job_id, job_type, job.attempts)

        handler = self.dispatcher.get_handler(job_type)
        if not handler:
            async with async_session_factory() as session:
                repo = JobRepository(session)
                await repo.fail_job(job_id, lease_token, f"No handler registered for {job_type}", retryable=False)
                await session.commit()
            return True

        # Heartbeat task extends lease every 20 seconds while job executes
        heartbeat_stop = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(job_id, lease_token, heartbeat_stop)
        )

        try:
            await handler.handle(payload)
            async with async_session_factory() as session:
                repo = JobRepository(session)
                await repo.complete_job(job_id, lease_token)
                await session.commit()
            logger.info("Completed job %s", job_id)
        except Exception as e:
            logger.exception("Error executing job %s: %s", job_id, e)
            async with async_session_factory() as session:
                repo = JobRepository(session)
                await repo.fail_job(job_id, lease_token, str(e), retryable=True)
                await session.commit()
        finally:
            heartbeat_stop.set()
            await heartbeat_task

        return True

    async def _heartbeat_loop(self, job_id: Any, lease_token: str, stop_event: asyncio.Event) -> None:
        """Extends lease every 20 seconds."""
        renewal_interval = max(5, self.lease_duration_seconds // 3)
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=renewal_interval)
            except asyncio.TimeoutError:
                async with async_session_factory() as session:
                    repo = JobRepository(session)
                    renewed = await repo.renew_lease(job_id, lease_token, extension_seconds=self.lease_duration_seconds)
                    await session.commit()
                    if not renewed:
                        logger.warning("Failed to renew lease for job %s; stopping heartbeat.", job_id)
                        break

    async def _scheduler_loop(self) -> None:
        """Periodic scheduler that enqueues scheduled sync tasks."""
        logger.info("Worker scheduler loop started (interval: %ds)", self.sync_interval_seconds)
        while self.is_running:
            try:
                await asyncio.sleep(self.sync_interval_seconds)
                # Enqueue periodic sync job with deduplication key per interval
                async with async_session_factory() as session:
                    repo = JobRepository(session)
                    await repo.enqueue(
                        job_type="sync_mailbox",
                        payload={"trigger": "scheduled"},
                        unique_key="scheduled_sync_mailbox",
                        priority=1,
                    )
                    await session.commit()
                    logger.debug("Scheduled mailbox sync check enqueued.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)


async def main():
    """Main worker process entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    dispatcher = create_default_dispatcher()
    worker = BackgroundWorker(dispatcher=dispatcher)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            # Signal handling on Windows
            pass

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

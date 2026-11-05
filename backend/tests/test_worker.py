import asyncio
import pytest
from app.db.session import async_session_factory
from app.jobs.dispatcher import JobDispatcher
from app.jobs.repository import JobRepository
from app.models.jobs import Job
from app.worker import BackgroundWorker


class MockHandler:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.handled_payloads = []

    async def handle(self, payload: dict) -> None:
        if self.should_fail:
            raise RuntimeError("Handler failed on purpose")
        self.handled_payloads.append(payload)


@pytest.mark.asyncio
async def test_worker_claim_execute_and_complete():
    dispatcher = JobDispatcher()
    mock_handler = MockHandler()
    dispatcher.register("mock_job", mock_handler)

    # 1. Enqueue job
    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.enqueue(
            job_type="mock_job",
            payload={"action": "test_run"},
            priority=10,
        )
        await session.commit()
        job_id = job.id

    # 2. Run worker for one iteration
    worker = BackgroundWorker(dispatcher=dispatcher, poll_interval_seconds=0.1)
    claimed = await worker._claim_and_execute_one()
    assert claimed is True
    assert len(mock_handler.handled_payloads) == 1
    assert mock_handler.handled_payloads[0] == {"action": "test_run"}

    # 3. Verify status in database
    async with async_session_factory() as session:
        job_db = await session.get(Job, job_id)
        assert job_db.status == "completed"
        assert job_db.completed_at is not None
        assert job_db.lease_token is None


@pytest.mark.asyncio
async def test_worker_failure_and_retry():
    dispatcher = JobDispatcher()
    mock_failing_handler = MockHandler(should_fail=True)
    dispatcher.register("failing_job", mock_failing_handler)

    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.enqueue(
            job_type="failing_job",
            payload={"info": "error_test"},
            max_attempts=2,
        )
        await session.commit()
        job_id = job.id

    worker = BackgroundWorker(dispatcher=dispatcher, poll_interval_seconds=0.1)

    # Attempt 1 -> fails, resets to 'queued' since attempts (1) < max_attempts (2)
    await worker._claim_and_execute_one()
    async with async_session_factory() as session:
        job_db = await session.get(Job, job_id)
        assert job_db.status == "queued"
        assert job_db.attempts == 1
        assert "Handler failed on purpose" in job_db.last_error

    # Attempt 2 -> fails, transitions to 'failed' because attempts (2) >= max_attempts (2)
    await worker._claim_and_execute_one()
    async with async_session_factory() as session:
        job_db = await session.get(Job, job_id)
        assert job_db.status == "failed"
        assert job_db.attempts == 2

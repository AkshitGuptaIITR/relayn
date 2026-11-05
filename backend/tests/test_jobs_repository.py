import datetime
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory
from app.jobs.repository import JobRepository
from app.models.jobs import Job


@pytest.mark.asyncio
async def test_enqueue_and_atomic_claim():
    key = f"unique_task_{uuid.uuid4().hex[:8]}"
    async with async_session_factory() as session:
        repo = JobRepository(session)

        # 1. Enqueue job
        job = await repo.enqueue(
            job_type="test_task",
            payload={"test_key": "val_1"},
            unique_key=key,
            priority=5,
        )
        await session.commit()
        assert job.status == "queued"
        assert job.attempts == 0

    # 2. Claim job in new session
    async with async_session_factory() as session:
        repo = JobRepository(session)
        claimed = await repo.claim_next_job(job_types=["test_task"])
        assert claimed is not None
        assert claimed.id == job.id
        assert claimed.status == "running"
        assert claimed.lease_token is not None
        assert claimed.attempts == 1

        # While running, another concurrent worker cannot claim it
        claimed_again = await repo.claim_next_job(job_types=["test_task"])
        assert claimed_again is None

        # 3. Complete job with matching lease token
        success = await repo.complete_job(claimed.id, claimed.lease_token)
        assert success is True
        await session.commit()

    # 4. Verify completed
    async with async_session_factory() as session:
        repo = JobRepository(session)
        claimed_completed = await repo.claim_next_job(job_types=["test_task"])
        assert claimed_completed is None


@pytest.mark.asyncio
async def test_expired_lease_recovery():
    async with async_session_factory() as session:
        repo = JobRepository(session)
        job = await repo.enqueue(
            job_type="recoverable_task",
            payload={"msg": "crash"},
            priority=10,
        )
        await session.commit()

    # Worker 1 claims job with 1-second lease
    async with async_session_factory() as session:
        repo = JobRepository(session)
        claimed = await repo.claim_next_job(job_types=["recoverable_task"], lease_duration_seconds=1)
        assert claimed is not None
        
        # Simulate worker crash: forcibly backdate leased_until
        claimed.leased_until = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=10)
        await session.commit()

    # Worker 2 comes along and recovers the expired lease
    async with async_session_factory() as session:
        repo = JobRepository(session)
        recovered = await repo.claim_next_job(job_types=["recoverable_task"], lease_duration_seconds=60)
        assert recovered is not None
        assert recovered.id == job.id
        assert recovered.attempts == 2

        # Complete and finish
        await repo.complete_job(recovered.id, recovered.lease_token)
        await session.commit()


@pytest.mark.asyncio
async def test_generation_fencing_cancellation():
    async with async_session_factory() as session:
        repo = JobRepository(session)
        job_old = await repo.enqueue(
            job_type="process_email",
            payload={"email_id": "1"},
            generation=1,
        )
        job_new = await repo.enqueue(
            job_type="process_email",
            payload={"email_id": "2"},
            generation=2,
        )
        await session.commit()

        # Disconnect/purge increments generation to 2, cancelling generation 1
        cancelled_count = await repo.cancel_generation(generation=2)
        assert cancelled_count >= 1
        await session.commit()

    async with async_session_factory() as session:
        res = await session.get(Job, job_old.id)
        assert res.status == "cancelled"

        res_new = await session.get(Job, job_new.id)
        assert res_new.status == "queued"

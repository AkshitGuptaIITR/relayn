import datetime
import secrets
import uuid
from typing import Any
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.jobs import Job


class JobRepository:
    """
    Durable PostgreSQL-backed queue operations using atomic row locking:
    - Atomically claims queued or expired lease jobs with SELECT ... FOR UPDATE SKIP LOCKED
    - Validates lease tokens before committing results
    - Handles retry backoff and generation fencing
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        unique_key: str | None = None,
        priority: int = 0,
        generation: int = 1,
        max_attempts: int = 3,
    ) -> Job:
        """
        Enqueues a job. If unique_key is provided and already exists:
        - If existing job is running/queued/completed, returns the existing job (idempotent).
        - If failed/cancelled, resets it to queued.
        """
        if unique_key:
            stmt = select(Job).where(Job.unique_key == unique_key)
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                if existing.status in ("queued", "running", "completed"):
                    return existing
                # Reset failed or cancelled job for retry
                existing.status = "queued"
                existing.payload = payload
                existing.priority = priority
                existing.generation = generation
                existing.attempts = 0
                existing.last_error = None
                existing.lease_token = None
                existing.leased_until = None
                await self.session.flush()
                return existing

        job = Job(
            job_type=job_type,
            unique_key=unique_key,
            payload=payload,
            priority=priority,
            generation=generation,
            max_attempts=max_attempts,
            status="queued",
            attempts=0,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def claim_next_job(
        self,
        job_types: list[str] | None = None,
        lease_duration_seconds: int = 60,
    ) -> Job | None:
        """
        Atomically claims the highest priority eligible job:
        1. status == 'queued'
        OR
        2. status == 'running' AND leased_until < now (expired lease recovery)
        Uses FOR UPDATE SKIP LOCKED to prevent lock contention across workers.
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        conditions = [
            or_(
                Job.status == "queued",
                (Job.status == "running") & (Job.leased_until < now),
            ),
            Job.attempts < Job.max_attempts,
        ]

        if job_types:
            conditions.append(Job.job_type.in_(job_types))

        stmt = (
            select(Job)
            .where(*conditions)
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            return None

        # Issue lease token and update state
        lease_token = secrets.token_hex(16)
        job.status = "running"
        job.lease_token = lease_token
        job.leased_until = now + datetime.timedelta(seconds=lease_duration_seconds)
        job.attempts += 1

        await self.session.flush()
        return job

    async def renew_lease(
        self,
        job_id: uuid.UUID,
        lease_token: str,
        extension_seconds: int = 60,
    ) -> bool:
        """Heartbeat renewal: Extends lease_until if lease_token matches and status is running."""
        now = datetime.datetime.now(datetime.timezone.utc)
        new_expiry = now + datetime.timedelta(seconds=extension_seconds)

        stmt = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.lease_token == lease_token,
                Job.status == "running",
            )
            .values(leased_until=new_expiry)
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def complete_job(
        self,
        job_id: uuid.UUID,
        lease_token: str,
    ) -> bool:
        """Marks job as completed, clearing lease."""
        now = datetime.datetime.now(datetime.timezone.utc)
        stmt = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.lease_token == lease_token,
                Job.status == "running",
            )
            .values(
                status="completed",
                completed_at=now,
                lease_token=None,
                leased_until=None,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def fail_job(
        self,
        job_id: uuid.UUID,
        lease_token: str,
        error_message: str,
        retryable: bool = True,
    ) -> bool:
        """
        Marks job failure.
        If retryable and attempts < max_attempts, resets to 'queued' for backoff retry.
        Otherwise marks as 'failed'.
        """
        stmt = select(Job).where(Job.id == job_id, Job.lease_token == lease_token)
        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()

        if not job:
            return False

        job.last_error = error_message
        job.lease_token = None
        job.leased_until = None

        if retryable and job.attempts < job.max_attempts:
            job.status = "queued"
        else:
            job.status = "failed"

        await self.session.flush()
        return True

    async def cancel_generation(self, generation: int) -> int:
        """Cancels all queued or running jobs from an older mailbox generation (generation fencing)."""
        stmt = (
            update(Job)
            .where(
                Job.generation < generation,
                Job.status.in_(["queued", "running"]),
            )
            .values(
                status="cancelled",
                last_error=f"Cancelled due to mailbox generation fence (current: {generation})",
                lease_token=None,
                leased_until=None,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount

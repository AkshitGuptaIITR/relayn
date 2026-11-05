import datetime
import pytest
from sqlalchemy import func, select
from app.db.session import async_session_factory
from app.integrations.mailbox.synthetic import SyntheticMailboxGateway
from app.models.career import (
    Company,
    Contact,
    FollowUpTask,
    Milestone,
    Opportunity,
    OpportunityEvent,
)
from app.models.mailbox import EmailMessage, MailboxAccount
from app.services.pipeline import CareerPipelineService
from app.services.sync import MailboxSyncService


@pytest.mark.asyncio
async def test_end_to_end_pipeline_processing():
    # 1. Clean DB tables
    async with async_session_factory() as session:
        await session.execute(FollowUpTask.__table__.delete())
        await session.execute(Milestone.__table__.delete())
        await session.execute(OpportunityEvent.__table__.delete())
        await session.execute(Opportunity.__table__.delete())
        await session.execute(Contact.__table__.delete())
        await session.execute(Company.__table__.delete())
        await session.execute(EmailMessage.__table__.delete())
        await session.execute(MailboxAccount.__table__.delete())
        await session.commit()

    # 2. Sync synthetic emails
    gateway = SyntheticMailboxGateway()
    sync_service = MailboxSyncService(gateway=gateway)
    synced_count = await sync_service.sync_mailbox()
    assert synced_count > 0

    # 3. Process all emails through pipeline
    pipeline = CareerPipelineService()
    async with async_session_factory() as session:
        emails = (await session.execute(select(EmailMessage.id))).scalars().all()

    for email_id in emails:
        await pipeline.process_email_message(email_id)

    # 4. Verify entities created
    async with async_session_factory() as session:
        # Companies
        companies = (await session.execute(select(Company.name))).scalars().all()
        assert "Stripe" in companies
        assert "Meta" in companies
        assert "Datadog" in companies

        # Opportunities
        stripe_opp = (
            await session.execute(
                select(Opportunity)
                .join(Company)
                .where(Company.name == "Stripe")
            )
        ).scalar_one()

        # Stripe should have progressed all the way to 'offer'
        assert stripe_opp.status == "offer"
        assert stripe_opp.salary_text is not None
        assert "235,000" in stripe_opp.salary_text

        # Meta should be 'rejected'
        meta_opp = (
            await session.execute(
                select(Opportunity)
                .join(Company)
                .where(Company.name == "Meta")
            )
        ).scalar_one()
        assert meta_opp.status == "rejected"

        # Events and Follow-ups created
        events_count = (await session.execute(select(func.count(OpportunityEvent.id)))).scalar()
        assert events_count > 0

        follow_ups_count = (await session.execute(select(func.count(FollowUpTask.id)))).scalar()
        assert follow_ups_count > 0

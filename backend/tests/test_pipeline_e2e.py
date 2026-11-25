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
    synced_count = await sync_service.sync_mailbox(limit=500)
    assert synced_count > 0

    # 3. Process all emails through pipeline
    from app.integrations.llm.fixtures import DeterministicFixtureProvider
    pipeline = CareerPipelineService(llm_provider=DeterministicFixtureProvider())
    async with async_session_factory() as session:
        emails = (await session.execute(select(EmailMessage.id).order_by(EmailMessage.sent_at.asc()))).scalars().all()

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

        # Datadog should have exactly ONE opportunity, not duplicated, progressing to 'interviewing'
        datadog_opps = (
            await session.execute(
                select(Opportunity)
                .join(Company)
                .where(Company.name == "Datadog")
            )
        ).scalars().all()
        assert len(datadog_opps) == 1
        assert datadog_opps[0].status == "interviewing"

        # Airbnb should have exactly ONE opportunity, not duplicated, progressing to 'rejected'
        airbnb_opps = (
            await session.execute(
                select(Opportunity)
                .join(Company)
                .where(Company.name == "Airbnb")
            )
        ).scalars().all()
        assert len(airbnb_opps) == 1
        assert airbnb_opps[0].status == "rejected"

        # Verify all emails have categories assigned
        categorized_emails = (
            await session.execute(
                select(EmailMessage)
                .where(EmailMessage.primary_category.isnot(None))
            )
        ).scalars().all()
        assert len(categorized_emails) == len(emails)

        # Events and Follow-ups created
        events_count = (await session.execute(select(func.count(OpportunityEvent.id)))).scalar()
        assert events_count > 0

        follow_ups_count = (await session.execute(select(func.count(FollowUpTask.id)))).scalar()
        assert follow_ups_count > 0


@pytest.mark.asyncio
async def test_outbound_outreach_and_reply_pipeline():
    from app.integrations.llm.fixtures import DeterministicFixtureProvider
    from app.integrations.mailbox.gateway import IngestedMessage, SyncResult
    from app.models.career import ReviewProposal

    class OutboundPipelineGateway:
        async def fetch_messages(self, after_history_id=None, limit=50):
            base_time = datetime.datetime(2026, 11, 20, 10, 0, tzinfo=datetime.timezone.utc)
            return SyncResult(
                messages=[
                    IngestedMessage(
                        gmail_message_id="msg_outreach_1",
                        gmail_thread_id="thread_outreach_1",
                        history_id="3001",
                        direction="outbound",
                        label_ids=["SENT"],
                        sender="demo.owner@relayn.local",
                        recipients=["Maya Lin <maya.lin@vercel.com>"],
                        subject="Reaching out about Staff Backend Engineer role at Vercel",
                        sent_at=base_time,
                        body_plain="Hi Maya, I am reaching out regarding open Staff Backend Engineer roles at Vercel.",
                    ),
                    IngestedMessage(
                        gmail_message_id="msg_outreach_reply_1",
                        gmail_thread_id="thread_outreach_1",
                        history_id="3002",
                        direction="outbound",
                        label_ids=["SENT"],
                        sender="demo.owner@relayn.local",
                        recipients=["Maya Lin <maya.lin@vercel.com>"],
                        subject="Re: Reaching out about Staff Backend Engineer role at Vercel",
                        sent_at=base_time + datetime.timedelta(days=1),
                        body_plain="Thursday at 2pm works for me. Looking forward to chatting!",
                    ),
                ],
                new_history_id="3002",
                has_more=False,
            )

    async with async_session_factory() as session:
        await session.execute(ReviewProposal.__table__.delete())
        await session.execute(FollowUpTask.__table__.delete())
        await session.execute(Milestone.__table__.delete())
        await session.execute(OpportunityEvent.__table__.delete())
        await session.execute(Opportunity.__table__.delete())
        await session.execute(Contact.__table__.delete())
        await session.execute(Company.__table__.delete())
        await session.execute(EmailMessage.__table__.delete())
        await session.execute(MailboxAccount.__table__.delete())
        await session.commit()

    sync_service = MailboxSyncService(gateway=OutboundPipelineGateway())
    synced = await sync_service.sync_mailbox(limit=10)
    assert synced == 2

    pipeline = CareerPipelineService(llm_provider=DeterministicFixtureProvider())
    async with async_session_factory() as session:
        email_ids = (await session.execute(select(EmailMessage.id).order_by(EmailMessage.sent_at.asc()))).scalars().all()

    for eid in email_ids:
        await pipeline.process_email_message(eid)

    async with async_session_factory() as session:
        opps = (await session.execute(select(Opportunity).join(Company).where(Company.name == "Vercel"))).scalars().all()
        assert len(opps) == 1
        assert opps[0].status == "lead"
        assert opps[0].opportunity_type == "lead"

        contacts = (await session.execute(select(Contact))).scalars().all()
        assert len(contacts) == 1
        assert contacts[0].email == "maya.lin@vercel.com"

        events = (await session.execute(select(OpportunityEvent).where(OpportunityEvent.opportunity_id == opps[0].id))).scalars().all()
        assert len(events) == 2
        assert {e.event_type for e in events} == {"candidate_outreach_sent", "candidate_reply_sent"}

        follow_ups = (await session.execute(select(FollowUpTask).where(FollowUpTask.opportunity_id == opps[0].id))).scalars().all()
        assert len(follow_ups) == 1
        assert follow_ups[0].due_date == datetime.date(2026, 11, 25)

        reviews = (await session.execute(select(ReviewProposal))).scalars().all()
        assert len(reviews) == 0

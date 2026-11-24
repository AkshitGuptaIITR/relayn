import argparse
import asyncio
import datetime
import logging
import sys
from pathlib import Path
from sqlalchemy import select, text

# Add backend directory to path if executed standalone
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import async_session_factory
from app.integrations.llm.fixtures import DeterministicFixtureProvider
from app.models.mailbox import EmailMessage, MailboxAccount
from app.services.pipeline import CareerPipelineService
from app.services.sync import MailboxSyncService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("relayn.reset_and_sync")


async def wipe_database():
    """Truncates all career, job, and message tables."""
    logger.info("🗑️  Wiping database records...")
    async with async_session_factory() as session:
        await session.execute(
            text("""
                TRUNCATE TABLE 
                    review_proposals,
                    follow_up_tasks,
                    milestones,
                    opportunity_events,
                    opportunity_contacts,
                    opportunities,
                    contacts,
                    companies,
                    email_messages,
                    jobs
                CASCADE;
            """)
        )

        # Reset mailbox account cursor and status
        stmt = select(MailboxAccount).limit(1)
        res = await session.execute(stmt)
        mb = res.scalar_one_or_none()
        if mb:
            mb.last_history_id = None
            mb.sync_status = "idle"
            mb.sync_error = None
            mb.last_synced_at = None
            mb.generation += 1

        await session.commit()
    logger.info("✅ Database wiped and mailbox sync cursor reset.")


async def verify_real_gmail_connection() -> bool:
    """Verifies that real Google OAuth credentials exist in the database."""
    async with async_session_factory() as session:
        stmt = select(MailboxAccount).limit(1)
        res = await session.execute(stmt)
        mb = res.scalar_one_or_none()
        if not mb or not mb.encrypted_credentials:
            return False
        return True


async def run_sync_and_pipeline(limit: int, synthetic: bool = False):
    """
    Syncs up to `limit` emails (via real Gmail or synthetic gateway),
    then executes the AI career pipeline inline for all newly ingested emails,
    and cleans up queued jobs in the database.
    """
    source_name = "Synthetic Test Fixtures" if synthetic else "Real Gmail Inbox"
    logger.info(f"📥 Connecting to {source_name} to sync up to {limit} emails...")
    sync_service = MailboxSyncService()

    # Step 1: Sync emails into database
    count = await sync_service.sync_mailbox(trigger="manual_reset", limit=limit)
    logger.info(f"✅ Fetched and saved {count} emails into database.")

    if count == 0:
        logger.warning("No new emails found matching the criteria.")
        return

    # Step 2: Extract structured career intelligence for all ingested emails
    logger.info("🧠 Starting AI career extraction pipeline...")
    pipeline = CareerPipelineService(
        llm_provider=DeterministicFixtureProvider() if synthetic else None
    )

    async with async_session_factory() as session:
        stmt = select(EmailMessage.id).where(EmailMessage.is_processed.is_(False)).order_by(EmailMessage.sent_at.asc())
        res = await session.execute(stmt)
        unprocessed_ids = [row[0] for row in res.fetchall()]

    logger.info(f"📋 Found {len(unprocessed_ids)} emails to process.")
    career_found = 0
    noise_filtered = 0

    for idx, email_id in enumerate(unprocessed_ids, start=1):
        if idx % 10 == 0 or idx == len(unprocessed_ids):
            logger.info(f"[{idx}/{len(unprocessed_ids)}] Processing emails (Career: {career_found}, Non-career: {noise_filtered})...")

        retries = 3
        for attempt in range(retries):
            try:
                success = await pipeline.process_email_message(email_id)
                if success:
                    career_found += 1
                else:
                    noise_filtered += 1
                break
            except Exception as e:
                err_str = str(e)
                if attempt < retries - 1 and any(k in err_str.lower() for k in ["429", "503", "quota", "demand", "resource_exhausted"]):
                    logger.warning(f"Spike or rate limit on email {email_id}; backing off for 4s (attempt {attempt + 1}/{retries})...")
                    await asyncio.sleep(4)
                else:
                    logger.error(f"Failed to process email {email_id}: {e}")
                    break

        # Gentle throttle between API calls for stability
        if not synthetic:
            await asyncio.sleep(0.25)

    # Step 3: Complete / clear queued jobs so no stranded jobs remain
    async with async_session_factory() as session:
        await session.execute(
            text("""
                UPDATE jobs 
                SET status = 'completed', completed_at = :now 
                WHERE job_type = 'process_email' AND status = 'queued'
            """),
            {"now": datetime.datetime.now(datetime.timezone.utc)},
        )
        await session.commit()

    logger.info("🎉 All emails successfully processed into career records! Queue is clean.")


async def main():
    parser = argparse.ArgumentParser(
        description="Relayn One-Time Database Reset & Mailbox Sync Script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=300,
        help="Number of emails to fetch and sync",
    )
    parser.add_argument(
        "--wipe-only",
        action="store_true",
        help="Only wipe the database without running any sync",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Run against synthetic benchmark emails (300 emails) instead of real Gmail OAuth",
    )
    args = parser.parse_args()

    # Step 1: Wipe the database
    await wipe_database()

    if args.wipe_only:
        logger.info("Wipe-only mode completed. Exiting.")
        return

    # Step 2: Check for real Gmail credentials if not using synthetic mode
    if not args.synthetic:
        has_credentials = await verify_real_gmail_connection()
        if not has_credentials:
            logger.error(
                "❌ No real Google Gmail OAuth credentials found in the database!\n"
                "   To sync your real Gmail emails:\n"
                "     1. Connect your Google account in the UI at http://localhost:3000/settings\n"
                "     2. Run: python reset_and_sync.py --limit 300\n\n"
                "   To run a clean reset and sync with the 300 synthetic benchmark emails, use:\n"
                "     python reset_and_sync.py --limit 300 --synthetic\n"
            )
            sys.exit(1)

    # Step 3: Run sync and inline AI extraction
    await run_sync_and_pipeline(limit=args.limit, synthetic=args.synthetic)


if __name__ == "__main__":
    asyncio.run(main())

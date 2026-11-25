import pytest
from app.integrations.llm.fixtures import DeterministicFixtureProvider


@pytest.mark.asyncio
async def test_deterministic_extraction_rejection():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="careers@meta.com",
        recipients=["me@relayn.local"],
        subject="Update regarding your application with Meta",
        body_plain="Thank you for taking the time. At this time we have decided to pursue other candidates for the Production Engineer role.",
    )
    assert res.is_career_related is True
    assert res.primary_category == "career_direct"
    assert res.lifecycle_intent == "rejection_notice"
    assert res.company_name == "Meta"
    assert res.current_stage == "rejected"
    assert res.event_type == "rejection_received"
    assert res.requires_human_review is False


@pytest.mark.asyncio
async def test_deterministic_extraction_offer():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="recruiter@stripe.com",
        recipients=["me@relayn.local"],
        subject="Congratulations! Offer from Stripe",
        body_plain="We are thrilled to formally extend an offer of employment for Staff Backend Engineer. Base Salary: $235,000",
    )
    assert res.is_career_related is True
    assert res.primary_category == "career_direct"
    assert res.lifecycle_intent == "offer_communication"
    assert res.company_name == "Stripe"
    assert res.current_stage == "offer"
    assert res.event_type == "offer_received"
    assert len(res.follow_ups) == 1
    assert "Review offer from Stripe" in res.follow_ups[0].title


@pytest.mark.asyncio
async def test_deterministic_extraction_noise_filtering():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="auto-confirm@amazon.com",
        recipients=["me@relayn.local"],
        subject="Your Amazon.com order #112-9847123 has shipped",
        body_plain="Your package has shipped and will arrive tomorrow.",
    )
    assert res.is_career_related is False
    assert res.primary_category == "non_career"
    assert res.lifecycle_intent == "irrelevant_noise"


@pytest.mark.asyncio
async def test_deterministic_extraction_job_board_digest():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="jobalerts-noreply@linkedin.com",
        recipients=["me@relayn.local"],
        subject="30 new jobs matching 'Staff Backend Engineer' - Job Alert",
        body_plain="Explore the latest open roles for Staff Backend Engineer in Seattle.",
    )
    assert res.is_career_related is False
    assert res.primary_category == "career_automated"
    assert res.lifecycle_intent == "job_digest"


@pytest.mark.asyncio
async def test_tech_company_non_career_notifications():
    provider = DeterministicFixtureProvider()
    
    # 1. GitHub security alert
    res_gh = await provider.extract_email(
        sender="notifications@github.com",
        recipients=["me@relayn.local"],
        subject="[GitHub] Security vulnerability alert for requests",
        body_plain="A high severity vulnerability was detected in your dependency graph.",
    )
    assert res_gh.is_career_related is False
    assert res_gh.primary_category == "non_career"
    assert res_gh.lifecycle_intent == "irrelevant_noise"

    # 2. Uber trip receipt
    res_uber = await provider.extract_email(
        sender="no-reply@uber.com",
        recipients=["me@relayn.local"],
        subject="Your trip with Uber on Saturday evening",
        body_plain="Thanks for riding with Uber. Total: $24.50. View your receipt.",
    )
    assert res_uber.is_career_related is False
    assert res_uber.primary_category == "non_career"
    assert res_uber.lifecycle_intent == "irrelevant_noise"


@pytest.mark.asyncio
async def test_candidate_referral_updates():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="careers@doordash.com",
        recipients=["me@relayn.local"],
        subject="Referral Received: Thank you for referring John Doe for Backend Engineer",
        body_plain="Thank you for referring John Doe. Our team has received their application.",
    )
    assert res.is_career_related is False
    assert res.primary_category == "career_automated"
    assert res.lifecycle_intent == "referral_update"


@pytest.mark.asyncio
async def test_candidate_interview_feedback_surveys():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="candidate-experience@meta.com",
        recipients=["me@relayn.local"],
        subject="Please rate your interview experience with Meta",
        body_plain="We would love your feedback on how your interview process went yesterday.",
    )
    assert res.is_career_related is False
    assert res.primary_category == "career_automated"
    assert res.lifecycle_intent == "interview_survey"


@pytest.mark.asyncio
async def test_coding_contest_marketing():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="contests@leetcode.com",
        recipients=["me@relayn.local"],
        subject="LeetCode Weekly Contest 390 is starting soon!",
        body_plain="Register now for the weekly contest and test your algorithmic problem solving.",
    )
    assert res.is_career_related is False
    assert res.primary_category == "career_automated"
    assert res.lifecycle_intent == "job_digest"


@pytest.mark.asyncio
async def test_outbound_cold_outreach_extraction():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="me@relayn.local",
        recipients=["Sarah Chen <sarah.chen@vercel.com>"],
        subject="Reaching out about Software Engineer opportunities at Vercel",
        body_plain="Hi Sarah, I am reaching out to express interest in an open Software Engineer role on your team.",
        direction="outbound",
    )
    assert res.is_career_related is True
    assert res.primary_category == "career_outreach"
    assert res.lifecycle_intent == "candidate_outreach"
    assert res.opportunity_type == "lead"
    assert res.current_stage == "lead"
    assert res.event_type == "candidate_outreach_sent"
    assert res.company_name == "Vercel"
    assert len(res.contacts) == 1
    assert res.contacts[0].email == "sarah.chen@vercel.com"


@pytest.mark.asyncio
async def test_outbound_direct_application_extraction():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="me@relayn.local",
        recipients=["jobs@linear.app"],
        subject="Applying for Staff Fullstack Engineer at Linear",
        body_plain="Hi team, attached is my resume for the Staff Fullstack Engineer position.",
        direction="outbound",
    )
    assert res.is_career_related is True
    assert res.primary_category == "career_direct"
    assert res.lifecycle_intent == "outbound_application"
    assert res.opportunity_type == "application"
    assert res.current_stage == "applied"
    assert res.event_type == "application_submitted"
    assert res.company_name == "Linear"
    assert len(res.contacts) == 1
    assert res.contacts[0].email == "jobs@linear.app"


@pytest.mark.asyncio
async def test_outbound_routine_reply_extraction():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="me@relayn.local",
        recipients=["recruiter@stripe.com"],
        subject="Re: Interview availability with Stripe",
        body_plain="Tuesday at 2pm works for me. Looking forward to speaking!",
        direction="outbound",
    )
    assert res.is_career_related is True
    assert res.primary_category == "career_direct"
    assert res.lifecycle_intent == "candidate_reply"
    assert res.current_stage is None
    assert res.event_type == "candidate_reply_sent"


@pytest.mark.asyncio
async def test_outbound_non_career_extraction():
    provider = DeterministicFixtureProvider()
    res = await provider.extract_email(
        sender="me@relayn.local",
        recipients=["friend@gmail.com"],
        subject="Dinner plans this Friday",
        body_plain="Hey, want to grab tacos at 7pm?",
        direction="outbound",
    )
    assert res.is_career_related is False
    assert res.primary_category == "non_career"
    assert res.lifecycle_intent == "irrelevant_noise"

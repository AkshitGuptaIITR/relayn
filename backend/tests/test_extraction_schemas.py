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

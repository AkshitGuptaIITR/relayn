import pytest
from app.db.session import engine


@pytest.fixture(autouse=True)
async def cleanup_db_connections():
    """Ensure async engine disposes connections per test."""
    yield
    await engine.dispose()

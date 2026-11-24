import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
import app.db.session as session_module

# Isolate test database from development database
TEST_DB_URL = "postgresql+asyncpg://postgres:root@localhost:5432/relayn_test"
settings.DATABASE_URL = TEST_DB_URL
settings.AI_PROVIDER = "fixtures"
settings.RELAYN_ENV = "test"

# Rebind database engine and sessionmaker to test database
test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    pool_pre_ping=True,
)
session_module.engine = test_engine
session_module.async_session_factory.configure(bind=test_engine)


@pytest.fixture(autouse=True)
async def cleanup_db_connections():
    """Ensure async engine disposes connections per test."""
    yield
    await session_module.engine.dispose()

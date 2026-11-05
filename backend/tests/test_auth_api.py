import pytest
from httpx import ASGITransport, AsyncClient
from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_auth_flow_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check unauthenticated me
        res = await client.get("/api/auth/me")
        assert res.status_code == 200
        assert res.json()["authenticated"] is False

        # 2. Login with wrong password
        res = await client.post("/api/auth/login", json={"password": "wrong_password_123"})
        assert res.status_code == 401
        assert "Invalid master password" in res.json()["detail"]

        # 3. Direct access to /api/auth/logout without cookie fails
        res = await client.post("/api/auth/logout")
        assert res.status_code == 401

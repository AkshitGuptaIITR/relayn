from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.auth import router as auth_router
from app.api.career import router as career_router
from app.api.google_oauth import router as google_oauth_router
from app.api.sync import router as sync_router


def create_app() -> FastAPI:
    """Application factory for Relayn backend."""
    app = FastAPI(
        title="Relayn API",
        description="Autonomous AI Career Management Agent API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # Register routers
    app.include_router(auth_router)
    app.include_router(career_router)
    app.include_router(google_oauth_router)
    app.include_router(sync_router)

    @app.get("/api/health")
    async def health_check():
        return {"status": "ok", "app": "relayn", "version": "0.1.0"}

    # Catch-all 404 handler for unknown /api/* routes
    @app.api_route("/api/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def api_not_found(request: Request, path_name: str):
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "message": f"API route '/api/{path_name}' not found"},
        )

    return app


app = create_app()

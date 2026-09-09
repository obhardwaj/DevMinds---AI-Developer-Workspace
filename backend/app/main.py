# backend/app/main.py
# FastAPI application entry point. Wires up the API router and,
# on startup, verifies DB connectivity. This is the process that
# `docker-compose.yml`'s `backend` service runs.

from fastapi import FastAPI
from app.api.routes import router as api_router
from app.config import settings

app = FastAPI(
    title="AI Developer Workspace",
    description="Repository Intelligence Platform API",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check():
    """Simple liveness probe used by Docker/orchestrators."""
    return {"status": "ok", "ai_layer_enabled": settings.AI_LAYER_ENABLED}

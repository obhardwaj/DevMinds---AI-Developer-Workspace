# backend/app/main.py
# FastAPI application entry point. Wires up the API router and,
# on startup, verifies DB connectivity. This is the process that
# `docker-compose.yml`'s `backend` service runs.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.config import settings

app = FastAPI(
    title="AI Developer Workspace",
    description="Repository Intelligence Platform API",
    version="0.1.0",
)

# Needed because the frontend (localhost:5173) and backend (localhost:8000)
# are different origins during local dev — without this, the browser
# blocks the frontend's fetch() calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check():
    """Simple liveness probe used by Docker/orchestrators."""
    return {"status": "ok", "ai_layer_enabled": settings.AI_LAYER_ENABLED}
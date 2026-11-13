"""AeroVault API — Phase 1 scaffold."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title="AeroVault API",
    version="0.1.0",
    description="Local aviation library and LLM decision-support tool.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": "AeroVault",
        "version": "0.1.0",
        "env": settings.env,
    }

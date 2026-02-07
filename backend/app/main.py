"""
PharmGuard AI - FastAPI application entry point.
CORS enabled; health check at GET /health; DB initialized on startup.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.api.routes import router as api_router
from app.api.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and any startup resources."""
    init_db()
    yield
    # shutdown if needed


app = FastAPI(
    title="PharmGuard AI",
    description="Agentic pharmacy system: conversational orders, prescription & stock rules, refill alerts.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(webhook_router, prefix="/api", tags=["webhook"])


@app.get("/health")
def health():
    """Health check for load balancers and readiness probes."""
    return {"status": "ok"}

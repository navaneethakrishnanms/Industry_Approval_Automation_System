"""
FastAPI Application Factory — the main entry point.

Startup sequence:
1. Create DB tables
2. Register all agents into AgentRegistry
3. Initialize LLM client (Gemini or Mock)
4. Load prompt registry from DB
5. Seed demo data if DB is empty
6. Configure CORS, rate limiting, middleware
7. Mount all routers
"""
from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_settings

settings = get_settings()


# ── Lifespan (startup/shutdown) ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    print(f"\n{'='*60}")
    print(f"  [AI] AI Workforce OS - Starting Up")
    print(f"  Version: {settings.app_version} | Env: {settings.app_env}")
    print(f"{'='*60}")

    # 1. Create database tables
    from app.database.base import create_all_tables, AsyncSessionLocal
    await create_all_tables()
    print("  [OK] Database tables created/verified")

    # 2. Register all agents
    from app.agents import register_all_agents
    register_all_agents()

    # 3. Initialize LLM client
    from app.core.llm_client import llm_client
    llm_client.initialize(settings.gemini_api_key or None, settings.effective_use_mock_llm)
    mode = "Mock LLM" if settings.effective_use_mock_llm else "Gemini Flash"
    print(f"  [OK] LLM Client initialized ({mode})")

    # 4. Wire EventBus to DB session factory
    from app.core.event_bus import event_bus
    event_bus.set_db_factory(AsyncSessionLocal)
    print("  [OK] Event Bus connected to database")

    # 5. Load prompts from DB + seed defaults
    async with AsyncSessionLocal() as session:
        from app.core.prompt_registry import prompt_registry
        await prompt_registry.seed_defaults_to_db(session)
        await prompt_registry.load_from_db(session)
    print("  [OK] Prompt Registry loaded")

    # 6. Check if demo data needs seeding
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        from app.models.tenant import Tenant
        count = await session.execute(select(func.count()).select_from(Tenant))
        if count.scalar_one() == 0:
            print("  [SEED] No data found - seeding synthetic demo data...")
            from demo_data.generator import generate_all
            await generate_all()
        else:
            print("  [OK] Demo data already present")

    print(f"\n  [READY] Server ready at http://0.0.0.0:8000")
    print(f"  [DOCS]  API Docs: http://0.0.0.0:8000/docs")
    print(f"{'='*60}\n")

    yield

    print("\n  [SHUTDOWN] AI Workforce OS - Shutting down\n")


# ── App Factory ────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Workforce OS",
        description="Hierarchical Multi-Agent AI Workforce Platform — Enterprise Demo",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request timing middleware ─────────────────────────────────────
    @app.middleware("http")
    async def add_timing_header(request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Response-Time-Ms"] = str(duration)
        return response

    # ── Health check ──────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health():
        from app.core.agent_registry import agent_registry
        from app.core.llm_client import llm_client
        return {
            "status": "healthy",
            "version": settings.app_version,
            "agents_registered": len(agent_registry.all_names()),
            "llm_mode": "mock" if settings.effective_use_mock_llm else "gemini",
            "demo_mode": settings.demo_mode,
        }

    @app.get("/", tags=["System"])
    async def root():
        return {
            "name": "AI Workforce OS",
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/health",
            "websocket": "ws://localhost:8000/ws/dashboard",
        }

    # ── Routers ───────────────────────────────────────────────────────
    from app.routers.workflow import router as workflow_router
    from app.routers.ws import router as ws_router
    from app.routers.routers import (
        agents_router, approvals_router, analytics_router,
        employees_router, demo_router, definitions_router,
        auth_router, prompts_router,
    )

    app.include_router(workflow_router)
    app.include_router(ws_router)
    app.include_router(agents_router)
    app.include_router(approvals_router)
    app.include_router(analytics_router)
    app.include_router(employees_router)
    app.include_router(demo_router)
    app.include_router(definitions_router)
    app.include_router(auth_router)
    app.include_router(prompts_router)

    return app


app = create_app()

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, engine
from app import models  # noqa: F401 -- register all ORM tables

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(bind=engine)

    if settings.scheduler_enabled:
        try:
            from app.services.scheduler import start_scheduler, shutdown_scheduler

            start_scheduler()
            logger.info("APScheduler started")
        except Exception as exc:
            logger.warning("Scheduler not started: %s", exc)

    yield

    if settings.scheduler_enabled:
        try:
            from app.services.scheduler import shutdown_scheduler
            shutdown_scheduler()
        except Exception:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        description="燃机性能监测系统 — 联合循环 / ISO 修正 / 性能退化 / 健康监测",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import (
        auth,
        users,
        gas_turbines,
        hrsg,
        steam_turbines,
        cc_units,
        readings,
        performance,
        baselines,
        alerts,
        dashboard,
        integration,
        upload,
    )

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(gas_turbines.router, prefix="/api/v1/gas-turbines", tags=["gas-turbines"])
    app.include_router(hrsg.router, prefix="/api/v1/hrsg", tags=["hrsg"])
    app.include_router(steam_turbines.router, prefix="/api/v1/steam-turbines", tags=["steam-turbines"])
    app.include_router(cc_units.router, prefix="/api/v1/cc-units", tags=["cc-units"])
    app.include_router(readings.router, prefix="/api/v1/readings", tags=["readings"])
    app.include_router(performance.router, prefix="/api/v1/performance", tags=["performance"])
    app.include_router(baselines.router, prefix="/api/v1/baselines", tags=["baselines"])
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(integration.router, prefix="/api/v1/integration", tags=["integration"])
    app.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])

    @app.get("/healthz", tags=["meta"])
    def healthz():
        return {"status": "ok", "service": "gas-turbine-performance"}

    return app


app = create_app()

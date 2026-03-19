"""FlightMatch FastAPI application factory."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.api.v1 import pilots, aircraft, missions, matches, calendar, admin, match


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed matching rules if DB is empty
    await _seed_matching_rules()
    yield
    # Shutdown: nothing to clean up


async def _seed_matching_rules():
    """Insert default matching rules if the table is empty."""
    try:
        from sqlalchemy import select, func
        from app.database import AsyncSessionLocal
        from app.models.matching import MatchingRule

        async with AsyncSessionLocal() as db:
            count = (await db.execute(select(func.count(MatchingRule.id)))).scalar()
            if count == 0:
                default_rules = [
                    MatchingRule(name="Active Status", rule_key="active_status", enabled=True,
                                 description="Pilot and at least one aircraft must be active"),
                    MatchingRule(name="Payload Capacity", rule_key="payload", enabled=True,
                                 description="Aircraft payload must meet mission requirements"),
                    MatchingRule(name="Range", rule_key="range", enabled=True,
                                 description="Aircraft range must meet mission min_range_nm"),
                    MatchingRule(name="Aircraft Type", rule_key="aircraft_type", enabled=True,
                                 description="Aircraft type must match mission requirements (if set)"),
                    MatchingRule(name="Oxygen Equipment", rule_key="oxygen", enabled=True,
                                 description="Aircraft must have oxygen if any passenger requires it"),
                    MatchingRule(name="IFR Equipment", rule_key="ifr", enabled=True,
                                 description="Aircraft must be IFR equipped"),
                    MatchingRule(name="Seat Count", rule_key="seats", enabled=True,
                                 description="Aircraft must have enough seats for all passengers"),
                    MatchingRule(name="Accessibility", rule_key="accessibility", enabled=True,
                                 description="Aircraft must be accessible if passenger has mobility equipment"),
                    MatchingRule(name="Pilot Availability", rule_key="availability", enabled=True,
                                 description="Pilot must not have busy calendar blocks during mission window"),
                    MatchingRule(name="Ferry Distance", rule_key="distance", enabled=True,
                                 description="Pilot home airport must be within ferry range of mission origin",
                                 parameters={"max_ferry_nm": 500}),
                ]
                for rule in default_rules:
                    db.add(rule)
                await db.commit()
    except Exception:
        pass  # DB may not be up yet


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="FlightMatch API",
        description="Humanitarian aviation pilot-mission matching service",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    prefix = "/api/v1"
    app.include_router(pilots.router, prefix=prefix)
    app.include_router(aircraft.router, prefix=prefix)
    app.include_router(missions.router, prefix=prefix)
    app.include_router(matches.router, prefix=prefix)
    app.include_router(calendar.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)
    app.include_router(match.router, prefix=prefix)

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "service": "flightmatch"}

    # Serve React UI from /ui/dist if it exists
    ui_dist = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")
    if os.path.isdir(ui_dist):
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")

    return app


app = create_app()

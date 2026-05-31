import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import engine, get_session
from .models.base import Base
from .models.admin_user import AdminUser
from .api.auth import router as auth_router, hash_password
from .api.health import router as health_router, update_service_status
from .api.pages import router as pages_router
from .api.channels import router as channels_router
from .api.weather import router as weather_router
from .api.tides import router as tides_router
from .api.tide_stations import router as tide_stations_router
from .api.fishing import router as fishing_router
from .api.fishing_locations import router as fishing_locations_router
from .api.surf import router as surf_router
from .api.surf_spots import router as surf_spots_router
from .api.settings import router as settings_router
from .api.admin import router as admin_router, install_log_ring_buffer, mark_started
from .api.lightning import router as lightning_router
from .services.lightning import lightning_service
from .services.settings_service import settings_service
from .services.tempest import weather_service
from .services.tides import tide_service
from .services.surf import surf_service
from .ws.routes import router as ws_router
from .ws.manager import ws_manager

settings = get_settings()
logger = logging.getLogger("signboard")


def ensure_settings_schema():
    """ALTER TABLE settings — add columns introduced with the Settings UI.

    SQLAlchemy's create_all() only creates missing tables; it does NOT add
    missing columns to existing ones. For SQLite, an ALTER TABLE ADD COLUMN
    is safe and idempotent when we check existing columns first.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "settings" not in inspector.get_table_names():
        return  # create_all() will build it fresh with the new schema

    existing = {c["name"] for c in inspector.get_columns("settings")}
    additions = [
        ('group', "VARCHAR(50) NOT NULL DEFAULT 'general'"),
        ('value_type', "VARCHAR(20) NOT NULL DEFAULT 'text'"),
        ('label', "VARCHAR(200) NOT NULL DEFAULT ''"),
        ('options', "VARCHAR(500)"),
        ('is_secret', "BOOLEAN NOT NULL DEFAULT 0"),
        ('is_readonly', "BOOLEAN NOT NULL DEFAULT 0"),
        ('sort_order', "INTEGER NOT NULL DEFAULT 0"),
    ]

    with engine.begin() as conn:
        for col, ddl in additions:
            if col not in existing:
                conn.execute(text(f'ALTER TABLE settings ADD COLUMN "{col}" {ddl}'))
                logger.info("settings: added column %s", col)


def seed_default_admin():
    """Create default admin user if none exists."""
    with get_session() as db:
        existing = db.query(AdminUser).first()
        if not existing:
            admin = AdminUser(
                username="admin",
                password_hash=hash_password(settings.default_admin_password),
                display_name="Administrator",
                must_change_password=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Created default admin user (username: admin)")


def seed_default_channels():
    """Create office and pool channels if none exist."""
    from .models.channel import Channel

    with get_session() as db:
        existing = db.query(Channel).first()
        if not existing:
            office = Channel(name="Marina Office", slug="office", rotation_interval=30)
            pool = Channel(name="Pool Area", slug="pool", rotation_interval=30)
            db.add_all([office, pool])
            db.commit()
            logger.info("Created default channels: office, pool")


def seed_system_pages():
    """Create system pages (weather, tides) if none exist."""
    from .models.page import Page

    with get_session() as db:
        required = [
            ("Current Weather", "weather_current"),
            ("5-Hour Forecast", "weather_hourly"),
            ("5-Day Forecast", "weather_forecast"),
            ("Tides", "tide_current"),
            ("Fishing Report", "fishing_report"),
            ("Surf Report", "surf_report"),
        ]
        for title, page_type in required:
            existing = db.query(Page).filter(Page.page_type == page_type).first()
            if not existing:
                db.add(Page(title=title, page_type=page_type, is_system=True, is_published=True))
                logger.info("Created system page: %s", page_type)
        db.commit()


def seed_surf_spots():
    """Seed ocean-facing surf spots on first run."""
    from .models.surf_spot import SurfSpot

    with get_session() as db:
        if db.query(SurfSpot).first():
            return

        seeds = [
            # NJ Atlantic coast faces roughly east (90°), so shore_facing_deg=90
            {"name": "Monmouth Beach", "latitude": 40.3340, "longitude": -73.9780,
             "shore_facing_deg": 90, "is_local": True, "sort_order": 0},
            {"name": "Long Branch Fishing Pier", "latitude": 40.2970, "longitude": -73.9780,
             "shore_facing_deg": 90, "sort_order": 1},
            {"name": "Shrewsbury Rocks", "latitude": 40.3700, "longitude": -73.9400,
             "shore_facing_deg": 90, "sort_order": 2},
            {"name": "Sandy Hook", "latitude": 40.4670, "longitude": -73.9770,
             "shore_facing_deg": 90, "sort_order": 3},
        ]
        for s in seeds:
            db.add(SurfSpot(**s, enabled=True))
        db.commit()
        logger.info("Seeded %d surf spots", len(seeds))


def seed_fishing_locations():
    """Seed Monmouth County NJ fishing locations on first run."""
    from .models.fishing_location import FishingLocation
    from .models.tide_station import TideStation

    with get_session() as db:
        if db.query(FishingLocation).first():
            return

        # Map NOAA station IDs to DB station IDs
        stations = {s.noaa_id: s.id for s in db.query(TideStation).all()}

        seeds = [
            {
                "name": "Shrewsbury River",
                "latitude": 40.3300, "longitude": -74.0000,
                "tide_station_noaa": "8531712",  # Long Branch Reach
                "is_local": True,
                "sort_order": 0,
            },
            {
                "name": "Monmouth Beach",
                "latitude": 40.3340, "longitude": -73.9780,
                "tide_station_noaa": "8531991",  # Long Branch Fishing Pier
                "sort_order": 1,
            },
            {
                "name": "Shrewsbury Rocks",
                "latitude": 40.3700, "longitude": -73.9400,
                "tide_station_noaa": "8531680",  # Sandy Hook
                "sort_order": 2,
            },
            {
                "name": "Raritan Bay",
                "latitude": 40.4800, "longitude": -74.2500,
                "tide_station_noaa": "8531680",  # Sandy Hook — nearest MLLW ref station
                "sort_order": 3,
            },
        ]

        for s in seeds:
            station_noaa = s.pop("tide_station_noaa")
            db.add(FishingLocation(
                **s,
                tide_station_id=stations.get(station_noaa),
                enabled=True,
            ))
        db.commit()
        logger.info("Seeded %d fishing locations", len(seeds))


def seed_tide_stations():
    """Seed tide stations from NOAA_STATIONS env on first run."""
    from .models.tide_station import TideStation

    with get_session() as db:
        if db.query(TideStation).first():
            return

        # Parse "id:name[:local],id:name[:local]"
        entries = []
        raw = settings.noaa_stations.strip()
        if raw:
            for i, chunk in enumerate(raw.split(",")):
                parts = chunk.strip().split(":")
                if len(parts) < 2:
                    continue
                entries.append({
                    "noaa_id": parts[0].strip(),
                    "name": parts[1].strip(),
                    "is_local": len(parts) > 2 and parts[2].strip().lower() == "local",
                    "sort_order": i,
                })
        # Fallback: legacy single-station env var
        if not entries and settings.noaa_station_id:
            entries.append({"noaa_id": settings.noaa_station_id, "name": "Tide Station", "is_local": True, "sort_order": 0})

        for e in entries:
            db.add(TideStation(**e, enabled=True))
        if entries:
            db.commit()
            logger.info("Seeded %d tide stations", len(entries))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    install_log_ring_buffer()
    mark_started()
    logger.info("SignBoard starting up...")

    # Create tables
    Base.metadata.create_all(bind=engine)
    ensure_settings_schema()
    logger.info("Database tables created/verified")

    # Seed data
    seed_default_admin()
    seed_default_channels()
    seed_system_pages()
    seed_tide_stations()
    seed_fishing_locations()
    seed_surf_spots()
    settings_service.seed_defaults()

    # Ensure uploads directory exists
    os.makedirs(settings.uploads_dir, exist_ok=True)

    # Mark database as healthy
    update_service_status("database", "healthy")

    # Start background services
    await weather_service.start()
    await tide_service.start()
    await surf_service.start()
    await lightning_service.start()

    yield

    # Stop background services
    await weather_service.stop()
    await tide_service.stop()
    await surf_service.stop()
    await lightning_service.stop()

    # Shutdown
    logger.info("SignBoard shutting down...")


app = FastAPI(
    title="SignBoard",
    description="Wharfside Manor Digital Signage System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(pages_router)
app.include_router(channels_router)
app.include_router(weather_router)
app.include_router(tides_router)
app.include_router(tide_stations_router)
app.include_router(fishing_router)
app.include_router(fishing_locations_router)
app.include_router(surf_router)
app.include_router(surf_spots_router)
app.include_router(settings_router)
app.include_router(admin_router)
app.include_router(lightning_router)
app.include_router(ws_router)

# Serve uploaded files
if os.path.exists(settings.uploads_dir):
    app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")

# Serve React frontend (built files) with SPA fallback
client_dist = os.path.join(os.path.dirname(__file__), "..", "client", "dist")
if os.path.exists(client_dist):
    from fastapi.responses import FileResponse

    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(client_dist, "assets")), name="assets")

    # SPA fallback: serve index.html for any unmatched route
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # Try to serve the exact file first (favicon.svg, icons.svg, etc.)
        file_path = os.path.join(client_dist, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse(os.path.join(client_dist, "index.html"))

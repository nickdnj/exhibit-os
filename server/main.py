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
from .api.settings import router as settings_router
from .api.admin import router as admin_router, install_log_ring_buffer, mark_started
from .services.settings_service import settings_service
from .ws.routes import router as ws_router
from .ws.manager import ws_manager

settings = get_settings()
logger = logging.getLogger("exhibitos")


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
    """Create default display channels if none exist."""
    from .models.channel import Channel

    with get_session() as db:
        existing = db.query(Channel).first()
        if not existing:
            lobby = Channel(name="Lobby", slug="lobby", rotation_interval=30)
            gallery = Channel(name="Gallery", slug="gallery", rotation_interval=30)
            db.add_all([lobby, gallery])
            db.commit()
            logger.info("Created default channels: lobby, gallery")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    install_log_ring_buffer()
    mark_started()
    logger.info("ExhibitOS starting up...")

    # Create tables
    Base.metadata.create_all(bind=engine)
    ensure_settings_schema()
    logger.info("Database tables created/verified")

    # Seed data
    seed_default_admin()
    seed_default_channels()
    settings_service.seed_defaults()

    # Ensure uploads directory exists
    os.makedirs(settings.uploads_dir, exist_ok=True)

    # Mark database as healthy
    update_service_status("database", "healthy")

    yield

    # Shutdown
    logger.info("ExhibitOS shutting down...")


app = FastAPI(
    title="ExhibitOS",
    description="Open information-display platform for museums and exhibits",
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
app.include_router(settings_router)
app.include_router(admin_router)
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

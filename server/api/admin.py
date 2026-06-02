"""Admin maintenance endpoints — log viewer, DB backup, system info."""
import logging
import os
import platform
import sqlite3
import sys
import tempfile
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from .auth import get_current_user
from ..config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ---- Log ring buffer ----

_MAX_LOGS = 500


class RingBufferHandler(logging.Handler):
    """In-memory ring buffer that keeps the last N formatted log lines."""

    def __init__(self, capacity: int = _MAX_LOGS):
        super().__init__()
        self.buffer: deque[dict] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append({
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
            })
        except Exception:
            self.handleError(record)

    def snapshot(self, limit: int, level: Optional[str] = None) -> list[dict]:
        items = list(self.buffer)
        if level:
            want = level.upper()
            items = [i for i in items if i["level"] == want]
        return items[-limit:]


_ring_handler: Optional[RingBufferHandler] = None


def install_log_ring_buffer():
    """Attach the ring buffer to the root exhibitos logger. Called at startup."""
    global _ring_handler
    if _ring_handler is not None:
        return _ring_handler
    _ring_handler = RingBufferHandler()
    _ring_handler.setLevel(logging.INFO)
    _ring_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger("exhibitos").addHandler(_ring_handler)
    # Also capture uvicorn access/error
    logging.getLogger("uvicorn").addHandler(_ring_handler)
    return _ring_handler


@router.get("/logs")
def get_logs(
    limit: int = 200,
    level: Optional[str] = None,
    _user=Depends(get_current_user),
):
    """Return the most recent server log lines."""
    if _ring_handler is None:
        return {"lines": [], "note": "log buffer not initialized"}
    limit = max(1, min(limit, _MAX_LOGS))
    return {"lines": _ring_handler.snapshot(limit, level)}


# ---- Database backup ----

@router.get("/backup")
def download_backup(_user=Depends(get_current_user)):
    """Stream a consistent SQLite snapshot to the caller."""
    settings = get_settings()
    # database_url looks like "sqlite:////data/exhibitos.db"
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    # Handle both sqlite:////abs/path and sqlite:///relative
    if db_path.startswith("/"):
        source = db_path
    else:
        source = os.path.abspath(db_path)

    if not os.path.exists(source):
        raise HTTPException(status_code=404, detail="Database file not found")

    # Use SQLite's online backup API for a consistent snapshot
    fd, tmp_path = tempfile.mkstemp(prefix="exhibitos-backup-", suffix=".db")
    os.close(fd)
    src_conn = sqlite3.connect(source)
    dst_conn = sqlite3.connect(tmp_path)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    filename = f"exhibitos-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    return FileResponse(tmp_path, media_type="application/octet-stream", filename=filename)


# ---- System info ----

@router.get("/info")
def system_info(_user=Depends(get_current_user)):
    """Read-only system metadata for the About panel."""
    settings = get_settings()
    try:
        import fastapi as _fastapi
        fastapi_version = _fastapi.__version__
    except Exception:
        fastapi_version = "unknown"

    # Disk usage for the data volume
    try:
        stat = os.statvfs(settings.uploads_dir)
        total_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        disk = {"total_gb": round(total_gb, 2), "free_gb": round(free_gb, 2)}
    except Exception:
        disk = {"total_gb": None, "free_gb": None}

    # DB size
    db_path = settings.database_url.replace("sqlite:///", "", 1)
    try:
        db_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else None
    except Exception:
        db_size_bytes = None

    return {
        "version": os.environ.get("EXHIBITOS_VERSION", "0.1.0"),
        "python_version": sys.version.split()[0],
        "fastapi_version": fastapi_version,
        "platform": f"{platform.system()} {platform.release()}",
        "disk": disk,
        "database_size_bytes": db_size_bytes,
        "uploads_dir": settings.uploads_dir,
        "started_at": _started_at.isoformat() if _started_at else None,
    }


_started_at: Optional[datetime] = None


def mark_started():
    """Record startup time for uptime display."""
    global _started_at
    _started_at = datetime.now(timezone.utc)

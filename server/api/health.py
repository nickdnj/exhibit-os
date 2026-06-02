from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["health"])

# Service status tracking (updated by background services)
_service_status = {
    "database": {"status": "unknown", "last_check": None},
}


def update_service_status(service: str, status: str, last_data: datetime | None = None):
    if service in _service_status:
        _service_status[service]["status"] = status
        _service_status[service]["last_check"] = datetime.now(timezone.utc).isoformat()
        if last_data:
            _service_status[service]["last_data"] = last_data.isoformat()


@router.get("/health")
def health_check():
    overall = "healthy"
    for svc in _service_status.values():
        if svc["status"] == "error":
            overall = "degraded"
            break

    # Include WebSocket connection counts
    try:
        from ..ws.manager import ws_manager
        connections = ws_manager.get_status()
    except Exception:
        connections = {}

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": _service_status,
        "connections": connections,
    }

from fastapi import APIRouter

from ..services.tides import tide_service

router = APIRouter(prefix="/api/tides", tags=["tides"])


@router.get("")
def get_tides():
    """Public endpoint — returns current tide state and predictions."""
    return tide_service.get_current_state()

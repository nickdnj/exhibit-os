from fastapi import APIRouter

from ..services.fishing import fishing_service

router = APIRouter(prefix="/api/fishing", tags=["fishing"])


@router.get("")
def get_fishing_report():
    """Public endpoint — solunar fishing report for today."""
    return fishing_service.get_report()

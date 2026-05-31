from fastapi import APIRouter

from ..services.surf import surf_service

router = APIRouter(prefix="/api/surf", tags=["surf"])


@router.get("")
def get_surf_report():
    """Public endpoint — current surf conditions for all spots."""
    return surf_service.get_report()

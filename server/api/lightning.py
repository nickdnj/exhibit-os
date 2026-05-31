"""Public + admin endpoints for the lightning safety service."""
from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import get_current_user
from ..services.lightning import lightning_service

router = APIRouter(prefix="/api/lightning", tags=["lightning"])


@router.get("/state")
def get_state():
    """Public endpoint — displays read this to render LightningPage."""
    return lightning_service.get_state()


@router.post("/simulate")
def simulate_strike(
    distance_km: int = Query(5, ge=0, le=100),
    _user=Depends(get_current_user),
):
    """Admin-only: inject a synthetic strike into the SignBoard state machine.

    Useful for verifying the end-to-end display path without waiting for a storm.
    """
    if not 0 <= distance_km <= 100:
        raise HTTPException(status_code=400, detail="distance_km out of range")
    lightning_service.inject_test_strike(distance_km)
    return {"injected": {"distance_km": distance_km}, "state": lightning_service.get_state()}

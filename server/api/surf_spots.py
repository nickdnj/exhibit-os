from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.surf_spot import SurfSpot
from ..services.surf import surf_service
from .auth import get_current_user

router = APIRouter(prefix="/api/surf-spots", tags=["surf-spots"])


class SurfSpotCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    shore_facing_deg: int = 90
    is_local: bool = False
    enabled: bool = True
    sort_order: int = 0


class SurfSpotUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    shore_facing_deg: Optional[int] = None
    is_local: Optional[bool] = None
    enabled: Optional[bool] = None
    sort_order: Optional[int] = None


def to_dict(s: SurfSpot) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "shore_facing_deg": s.shore_facing_deg,
        "is_local": s.is_local,
        "enabled": s.enabled,
        "sort_order": s.sort_order,
    }


@router.get("")
def list_spots(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rows = db.query(SurfSpot).order_by(SurfSpot.sort_order, SurfSpot.id).all()
    return [to_dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_spot(req: SurfSpotCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if req.is_local:
        db.query(SurfSpot).update({SurfSpot.is_local: False})
    spot = SurfSpot(**req.model_dump())
    db.add(spot)
    db.commit()
    db.refresh(spot)
    await surf_service.reload()
    return to_dict(spot)


@router.put("/{spot_id}")
async def update_spot(spot_id: int, req: SurfSpotUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    spot = db.query(SurfSpot).filter(SurfSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")
    data = req.model_dump(exclude_unset=True)
    if data.get("is_local"):
        db.query(SurfSpot).filter(SurfSpot.id != spot_id).update({SurfSpot.is_local: False})
    for k, v in data.items():
        setattr(spot, k, v)
    db.commit()
    db.refresh(spot)
    await surf_service.reload()
    return to_dict(spot)


@router.delete("/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spot(spot_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    spot = db.query(SurfSpot).filter(SurfSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")
    db.delete(spot)
    db.commit()
    await surf_service.reload()

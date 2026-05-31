from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.fishing_location import FishingLocation
from .auth import get_current_user

router = APIRouter(prefix="/api/fishing-locations", tags=["fishing-locations"])


class FishingLocationCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    tide_station_id: Optional[int] = None
    is_local: bool = False
    enabled: bool = True
    sort_order: int = 0


class FishingLocationUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tide_station_id: Optional[int] = None
    is_local: Optional[bool] = None
    enabled: Optional[bool] = None
    sort_order: Optional[int] = None


def to_dict(loc: FishingLocation) -> dict:
    return {
        "id": loc.id,
        "name": loc.name,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "tide_station_id": loc.tide_station_id,
        "is_local": loc.is_local,
        "enabled": loc.enabled,
        "sort_order": loc.sort_order,
    }


@router.get("")
def list_locations(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rows = db.query(FishingLocation).order_by(FishingLocation.sort_order, FishingLocation.id).all()
    return [to_dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_location(req: FishingLocationCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    if req.is_local:
        db.query(FishingLocation).update({FishingLocation.is_local: False})
    loc = FishingLocation(**req.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return to_dict(loc)


@router.put("/{loc_id}")
def update_location(loc_id: int, req: FishingLocationUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    loc = db.query(FishingLocation).filter(FishingLocation.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    data = req.model_dump(exclude_unset=True)
    if data.get("is_local"):
        db.query(FishingLocation).filter(FishingLocation.id != loc_id).update({FishingLocation.is_local: False})
    for k, v in data.items():
        setattr(loc, k, v)
    db.commit()
    db.refresh(loc)
    return to_dict(loc)


@router.delete("/{loc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(loc_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    loc = db.query(FishingLocation).filter(FishingLocation.id == loc_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    db.delete(loc)
    db.commit()

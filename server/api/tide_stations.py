from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.tide_station import TideStation
from ..services.tides import tide_service
from .auth import get_current_user

router = APIRouter(prefix="/api/tide-stations", tags=["tide-stations"])


class TideStationCreate(BaseModel):
    noaa_id: str
    name: str
    is_local: bool = False
    enabled: bool = True
    sort_order: int = 0


class TideStationUpdate(BaseModel):
    noaa_id: Optional[str] = None
    name: Optional[str] = None
    is_local: Optional[bool] = None
    enabled: Optional[bool] = None
    sort_order: Optional[int] = None


def to_dict(s: TideStation) -> dict:
    return {
        "id": s.id,
        "noaa_id": s.noaa_id,
        "name": s.name,
        "is_local": s.is_local,
        "enabled": s.enabled,
        "sort_order": s.sort_order,
    }


@router.get("")
def list_stations(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    stations = db.query(TideStation).order_by(TideStation.sort_order, TideStation.id).all()
    return [to_dict(s) for s in stations]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_station(req: TideStationCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    existing = db.query(TideStation).filter(TideStation.noaa_id == req.noaa_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Station with this NOAA ID already exists")

    # Only one local station
    if req.is_local:
        db.query(TideStation).update({TideStation.is_local: False})

    station = TideStation(**req.model_dump())
    db.add(station)
    db.commit()
    db.refresh(station)
    await tide_service.reload()
    return to_dict(station)


@router.put("/{station_id}")
async def update_station(station_id: int, req: TideStationUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    station = db.query(TideStation).filter(TideStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    data = req.model_dump(exclude_unset=True)
    if data.get("is_local"):
        db.query(TideStation).filter(TideStation.id != station_id).update({TideStation.is_local: False})

    for key, value in data.items():
        setattr(station, key, value)

    db.commit()
    db.refresh(station)
    await tide_service.reload()
    return to_dict(station)


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(station_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    station = db.query(TideStation).filter(TideStation.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    db.delete(station)
    db.commit()
    await tide_service.reload()

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json

from ..database import get_db
from ..models.channel import Channel
from ..models.channel_page import ChannelPageAssignment
from ..models.page import Page
from ..models.announcement import Announcement
from .auth import get_current_user

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelCreate(BaseModel):
    name: str
    slug: str
    rotation_interval: int = 30


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    rotation_interval: Optional[int] = None
    is_active: Optional[bool] = None


class PageAssignment(BaseModel):
    page_id: int
    sort_order: int
    is_enabled: bool = True
    duration_override: Optional[int] = None


class BulkPageAssignment(BaseModel):
    pages: list[PageAssignment]


def channel_to_dict(channel: Channel, include_pages: bool = False) -> dict:
    result = {
        "id": channel.id,
        "name": channel.name,
        "slug": channel.slug,
        "rotation_interval": channel.rotation_interval,
        "is_active": channel.is_active,
        "page_count": len(channel.page_assignments) if channel.page_assignments else 0,
        "created_at": channel.created_at.isoformat() if channel.created_at else None,
    }
    if include_pages and channel.page_assignments:
        result["pages"] = [
            {
                "assignment_id": a.id,
                "page_id": a.page_id,
                "sort_order": a.sort_order,
                "is_enabled": a.is_enabled,
                "duration_override": a.duration_override,
                "page": {
                    "id": a.page.id,
                    "title": a.page.title,
                    "page_type": a.page.page_type,
                    "is_system": a.page.is_system,
                    "is_published": a.page.is_published,
                },
            }
            for a in sorted(channel.page_assignments, key=lambda x: x.sort_order)
        ]
    return result


@router.get("")
def list_channels(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    channels = db.query(Channel).order_by(Channel.id).all()
    return [channel_to_dict(c) for c in channels]


@router.get("/{channel_id}")
def get_channel(channel_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel_to_dict(channel, include_pages=True)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_channel(request: ChannelCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    existing = db.query(Channel).filter(Channel.slug == request.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Channel slug already exists")

    channel = Channel(name=request.name, slug=request.slug, rotation_interval=request.rotation_interval)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel_to_dict(channel)


@router.put("/{channel_id}")
def update_channel(channel_id: int, request: ChannelUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if request.name is not None:
        channel.name = request.name
    if request.rotation_interval is not None:
        channel.rotation_interval = request.rotation_interval
    if request.is_active is not None:
        channel.is_active = request.is_active

    db.commit()
    db.refresh(channel)
    from ..ws.manager import ws_manager
    ws_manager.notify_page_update_sync(channel.slug)
    return channel_to_dict(channel, include_pages=True)


@router.put("/{channel_id}/pages")
def assign_pages(channel_id: int, request: BulkPageAssignment, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Remove existing assignments
    db.query(ChannelPageAssignment).filter(ChannelPageAssignment.channel_id == channel_id).delete()

    # Create new assignments
    for item in request.pages:
        page = db.query(Page).filter(Page.id == item.page_id).first()
        if not page:
            raise HTTPException(status_code=400, detail=f"Page {item.page_id} not found")

        assignment = ChannelPageAssignment(
            channel_id=channel_id,
            page_id=item.page_id,
            sort_order=item.sort_order,
            is_enabled=item.is_enabled,
            duration_override=item.duration_override,
        )
        db.add(assignment)

    db.commit()
    db.refresh(channel)
    from ..ws.manager import ws_manager
    ws_manager.notify_page_update_sync(channel.slug)
    return channel_to_dict(channel, include_pages=True)


# --- Public display endpoint (no auth required) ---

@router.get("/{slug}/display")
def get_channel_display(slug: str, db: Session = Depends(get_db)):
    """Public endpoint for display clients. Returns channel config and active pages."""
    channel = db.query(Channel).filter(Channel.slug == slug, Channel.is_active == True).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    pages = []
    for assignment in sorted(channel.page_assignments, key=lambda x: x.sort_order):
        if not assignment.is_enabled:
            continue
        if not assignment.page.is_published:
            continue

        page_data = {
            "page_id": assignment.page.id,
            "title": assignment.page.title,
            "page_type": assignment.page.page_type,
            "config_json": json.loads(assignment.page.config_json) if assignment.page.config_json else None,
            "image_path": assignment.page.image_path,
            "duration": assignment.duration_override or channel.rotation_interval,
        }

        # Include announcement data if applicable
        if assignment.page.page_type == "announcement" and assignment.page.announcement:
            ann = assignment.page.announcement
            # Filter by date range
            if ann.starts_at and ann.starts_at > now:
                continue
            if ann.expires_at and ann.expires_at < now:
                continue
            page_data["announcement"] = {
                "body_text": ann.body_text,
                "priority": ann.priority,
            }

        pages.append(page_data)

    return {
        "channel": {
            "name": channel.name,
            "slug": channel.slug,
            "rotation_interval": channel.rotation_interval,
        },
        "pages": pages,
        "timestamp": now.isoformat(),
    }

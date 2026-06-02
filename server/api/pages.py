from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
import os
import shutil

from ..database import get_db
from ..config import get_settings
from ..models.page import Page
from ..models.announcement import Announcement
from .auth import get_current_user


def _notify_page_change():
    """Notify display clients that pages changed.

    Called from sync route handlers (threadpool, no event loop), so it schedules
    the broadcast onto the captured main loop rather than using create_task.
    """
    from ..ws.manager import ws_manager
    ws_manager.notify_page_update_sync()

router = APIRouter(prefix="/api/pages", tags=["pages"])
settings = get_settings()


class PageCreate(BaseModel):
    title: str
    page_type: str
    config_json: Optional[str] = None


class PageUpdate(BaseModel):
    title: Optional[str] = None
    config_json: Optional[str] = None
    is_published: Optional[bool] = None


class AnnouncementData(BaseModel):
    body_text: str
    priority: str = "normal"
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None


class PageWithAnnouncement(BaseModel):
    title: str
    page_type: str = "announcement"
    body_text: str
    priority: str = "normal"
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None


def page_to_dict(page: Page) -> dict:
    result = {
        "id": page.id,
        "title": page.title,
        "page_type": page.page_type,
        "is_system": page.is_system,
        "is_published": page.is_published,
        "config_json": json.loads(page.config_json) if page.config_json else None,
        "image_path": page.image_path,
        "created_at": page.created_at.isoformat() if page.created_at else None,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }
    if page.announcement:
        result["announcement"] = {
            "body_text": page.announcement.body_text,
            "priority": page.announcement.priority,
            "starts_at": page.announcement.starts_at.isoformat() if page.announcement.starts_at else None,
            "expires_at": page.announcement.expires_at.isoformat() if page.announcement.expires_at else None,
        }
    return result


@router.get("")
def list_pages(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    pages = db.query(Page).order_by(Page.id).all()
    return [page_to_dict(p) for p in pages]


@router.get("/{page_id}")
def get_page(page_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page_to_dict(page)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_page(request: PageCreate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    page = Page(
        title=request.title,
        page_type=request.page_type,
        config_json=request.config_json,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    _notify_page_change()
    return page_to_dict(page)


@router.post("/announcement", status_code=status.HTTP_201_CREATED)
def create_announcement(request: PageWithAnnouncement, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    from datetime import datetime

    page = Page(
        title=request.title,
        page_type="announcement",
    )
    db.add(page)
    db.flush()

    announcement = Announcement(
        page_id=page.id,
        body_text=request.body_text,
        priority=request.priority,
        starts_at=datetime.fromisoformat(request.starts_at) if request.starts_at else None,
        expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None,
    )
    db.add(announcement)
    db.commit()
    db.refresh(page)
    _notify_page_change()
    return page_to_dict(page)


@router.put("/{page_id}")
def update_page(page_id: int, request: PageUpdate, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    if request.title is not None:
        page.title = request.title
    if request.config_json is not None:
        page.config_json = request.config_json
    if request.is_published is not None:
        page.is_published = request.is_published

    db.commit()
    db.refresh(page)
    _notify_page_change()
    return page_to_dict(page)


@router.put("/{page_id}/announcement")
def update_announcement(
    page_id: int, request: AnnouncementData, db: Session = Depends(get_db), _user=Depends(get_current_user)
):
    from datetime import datetime

    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    if not page.announcement:
        announcement = Announcement(
            page_id=page.id,
            body_text=request.body_text,
            priority=request.priority,
            starts_at=datetime.fromisoformat(request.starts_at) if request.starts_at else None,
            expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None,
        )
        db.add(announcement)
    else:
        page.announcement.body_text = request.body_text
        page.announcement.priority = request.priority
        page.announcement.starts_at = datetime.fromisoformat(request.starts_at) if request.starts_at else None
        page.announcement.expires_at = datetime.fromisoformat(request.expires_at) if request.expires_at else None

    db.commit()
    db.refresh(page)
    _notify_page_change()
    return page_to_dict(page)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(page_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system pages")

    # Clean up image file if exists
    if page.image_path and os.path.exists(page.image_path):
        os.remove(page.image_path)

    db.delete(page)
    db.commit()
    _notify_page_change()


@router.post("/{page_id}/image")
async def upload_image(
    page_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    # Save file
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "jpg"
    filename = f"page_{page_id}.{ext}"
    filepath = os.path.join(settings.uploads_dir, filename)
    os.makedirs(settings.uploads_dir, exist_ok=True)

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    page.image_path = f"/uploads/{filename}"
    db.commit()
    db.refresh(page)
    _notify_page_change()
    return page_to_dict(page)

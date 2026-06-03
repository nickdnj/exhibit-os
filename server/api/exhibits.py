"""Exhibit API — public read for displays, authenticated re-ingest for admins.

Exhibit narrative content is authored in the docent wiki (ADR-0001) and pulled
in via the wiki-ingest service. These endpoints expose the local read-cache:
displays need public read access; only admins can trigger a re-ingest.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.exhibit import Exhibit
from ..services.wiki_ingest import ingest_from_file
from .auth import get_current_user

router = APIRouter(prefix="/api/exhibits", tags=["exhibits"])


def _exhibit_summary(e: Exhibit) -> dict:
    return {
        "slug": e.slug,
        "title": e.title,
        "year_introduced": e.year_introduced,
        "source_ref": e.source_ref,
        "has_hero": bool(e.hero_image),
        "has_video": bool(e.video_url),
    }


def _exhibit_full(e: Exhibit) -> dict:
    return {
        "slug": e.slug,
        "title": e.title,
        "year_introduced": e.year_introduced,
        "body_text": e.body_text,
        "key_facts": e.key_facts.split("\n") if e.key_facts else [],
        "people": e.people,
        "related_exhibits": e.related_exhibits,
        "source_ref": e.source_ref,
        "ingested_at": e.ingested_at.isoformat() if e.ingested_at else None,
        # ExhibitOS-owned display fields
        "hero_image": e.hero_image,
        "video_url": e.video_url,
        "deep_content_url": e.deep_content_url,
        "location": e.location,
    }


@router.get("")
def list_exhibits(db: Session = Depends(get_db)):
    """PUBLIC — displays need this. Lightweight list of all exhibits,
    in the docent wiki's approximate-chronological source order."""
    exhibits = db.query(Exhibit).order_by(Exhibit.sort_order, Exhibit.title).all()
    return [_exhibit_summary(e) for e in exhibits]


@router.post("/ingest")
def trigger_ingest(_user=Depends(get_current_user)):
    """AUTH — pull the latest exhibit content from the wiki export."""
    counts = ingest_from_file()
    return counts


@router.get("/{slug}")
def get_exhibit(slug: str, db: Session = Depends(get_db)):
    """PUBLIC — full interpretive content for one exhibit."""
    exhibit = db.query(Exhibit).filter(Exhibit.slug == slug).first()
    if not exhibit:
        raise HTTPException(status_code=404, detail="Exhibit not found")
    return _exhibit_full(exhibit)

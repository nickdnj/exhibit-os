from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .base import Base


class Exhibit(Base):
    """An exhibit's interpretive content, ingested from the docent wiki.

    The wiki (DokuWiki) is the system of record for the narrative fields
    (title, body_text, key_facts, people, year, related). ExhibitOS owns the
    display-side fields (hero_image, video_url, deep_content_url, location),
    which are NEVER overwritten by re-ingest. See ADR-0001.
    """

    __tablename__ = "exhibits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    year_introduced: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Source position in the docent wiki (approx. chronological) — drives display order.
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # Wiki-sourced narrative content (refreshed on re-ingest when content changes)
    body_text: Mapped[str] = mapped_column(Text, default="")
    key_facts: Mapped[str] = mapped_column(Text, default="")  # newline-joined bullets
    people: Mapped[str | None] = mapped_column(String(500), nullable=True)
    related_exhibits: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Provenance / idempotency
    source_ref: Mapped[str] = mapped_column(String(300))  # e.g. the_artifacts#<slug>
    content_hash: Mapped[str] = mapped_column(String(64))  # hash of parsed wiki content
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # ExhibitOS-owned display fields — NOT from wiki, preserved across re-ingest
    hero_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deep_content_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

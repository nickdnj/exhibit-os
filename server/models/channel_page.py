from sqlalchemy import Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class ChannelPageAssignment(Base):
    __tablename__ = "channel_page_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    page_id: Mapped[int] = mapped_column(ForeignKey("pages.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    duration_override: Mapped[int | None] = mapped_column(Integer, nullable=True)  # seconds, overrides channel default

    # Relationships
    channel = relationship("Channel", back_populates="page_assignments")
    page = relationship("Page", back_populates="channel_assignments")

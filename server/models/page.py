from sqlalchemy import String, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class Page(Base, TimestampMixin):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    page_type: Mapped[str] = mapped_column(String(50))  # weather_current, weather_forecast, tide, lightning, announcement, custom
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # system pages can't be deleted
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # type-specific config
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)  # draft vs published

    # Relationships
    channel_assignments = relationship("ChannelPageAssignment", back_populates="page", cascade="all, delete-orphan")
    announcement = relationship("Announcement", back_populates="page", uselist=False, cascade="all, delete-orphan")

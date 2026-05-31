from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(50), unique=True)  # URL path: /display/{slug}
    rotation_interval: Mapped[int] = mapped_column(Integer, default=30)  # seconds
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    page_assignments = relationship("ChannelPageAssignment", back_populates="channel", cascade="all, delete-orphan")

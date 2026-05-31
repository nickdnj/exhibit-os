from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class SurfSpot(Base, TimestampMixin):
    __tablename__ = "surf_spots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # Shoreline orientation in degrees — direction the beach faces (seaward).
    # Used to determine onshore vs offshore wind. NJ coast faces ~90° (east).
    shore_facing_deg: Mapped[int] = mapped_column(Integer, default=90)
    is_local: Mapped[bool] = mapped_column(default=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

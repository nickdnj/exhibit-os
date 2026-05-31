from sqlalchemy import String, Integer, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class FishingLocation(Base, TimestampMixin):
    __tablename__ = "fishing_locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    tide_station_id: Mapped[int | None] = mapped_column(
        ForeignKey("tide_stations.id", ondelete="SET NULL"), nullable=True
    )
    is_local: Mapped[bool] = mapped_column(default=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    tide_station = relationship("TideStation")

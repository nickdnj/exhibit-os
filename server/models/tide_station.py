from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class TideStation(Base, TimestampMixin):
    __tablename__ = "tide_stations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    noaa_id: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    is_local: Mapped[bool] = mapped_column(default=False)
    enabled: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

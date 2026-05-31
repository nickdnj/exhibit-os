from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text, default="")
    # Grouping & presentation metadata — used by /api/settings to render the UI
    group: Mapped[str] = mapped_column(String(50), default="general")
    value_type: Mapped[str] = mapped_column(String(20), default="text")  # text | number | toggle | dropdown | password
    label: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Comma-separated dropdown options (only used when value_type == "dropdown")
    options: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

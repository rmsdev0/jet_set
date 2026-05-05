from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSON_VARIANT


class Experience(BaseModel):
    __tablename__ = "experiences"

    lodge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lodges.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    sport_type: Mapped[str] = mapped_column(String(50), index=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_group_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_per_person: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    includes: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    season_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photos: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    lodge = relationship("Lodge", back_populates="experiences")
    availability_windows = relationship("Availability", back_populates="experience")

from __future__ import annotations

import uuid
from datetime import date
import enum

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AvailabilityStatus(str, enum.Enum):
    open = "open"
    full = "full"
    blocked = "blocked"


class Availability(BaseModel):
    __tablename__ = "availability"

    experience_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("experiences.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date)
    spots_total: Mapped[int] = mapped_column(Integer, nullable=False)
    spots_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    price_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[AvailabilityStatus] = mapped_column(
        SAEnum(AvailabilityStatus), default=AvailabilityStatus.open, nullable=False
    )

    experience = relationship("Experience", back_populates="availability_windows")
    bookings = relationship("Booking", back_populates="availability")

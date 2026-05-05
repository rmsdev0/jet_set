from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSON_VARIANT


class Review(BaseModel):
    __tablename__ = "reviews"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    lodge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lodges.id"), index=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"), unique=True)
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    sport_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    accommodation_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    guide_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    food_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    value_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    photos: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="reviews")
    lodge = relationship("Lodge", back_populates="reviews")
    booking = relationship("Booking", back_populates="review")

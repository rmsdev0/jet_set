from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSON_VARIANT


class Lodge(BaseModel):
    __tablename__ = "lodges"

    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sport_types: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    species_targeted: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    location_country: Mapped[str] = mapped_column(String(100), index=True)
    location_region: Mapped[str] = mapped_column(String(255), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    amenities: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    max_guests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photos: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stripe_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_claimed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_prospect_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("prospects.id"), nullable=True)
    cancellation_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cancellation_policies.id"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    rating_avg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starting_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_document: Mapped[str] = mapped_column(Text, default="", nullable=False)

    experiences = relationship("Experience", back_populates="lodge", lazy="selectin")
    reviews = relationship("Review", back_populates="lodge")
    owners = relationship("LodgeOwner", back_populates="lodge")
    claims = relationship("Claim", back_populates="lodge")
    bookings = relationship("Booking", back_populates="lodge")
    cancellation_policy = relationship("CancellationPolicy", back_populates="lodges")

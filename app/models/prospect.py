from __future__ import annotations

import uuid
import enum

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSON_VARIANT


class EnrichmentStatus(str, enum.Enum):
    pending = "pending"
    enriched = "enriched"
    failed = "failed"


class OutreachStatus(str, enum.Enum):
    not_contacted = "not_contacted"
    email_1_sent = "email_1_sent"
    email_2_sent = "email_2_sent"
    email_3_sent = "email_3_sent"
    replied = "replied"
    onboarded = "onboarded"
    declined = "declined"


class Prospect(BaseModel):
    __tablename__ = "prospects"

    name: Mapped[str] = mapped_column(String(255), index=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    sport_type_guess: Mapped[str | None] = mapped_column(String(50), nullable=True)
    species_guess: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instagram_handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instagram_followers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_scraped_data: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        SAEnum(EnrichmentStatus), default=EnrichmentStatus.pending
    )
    enriched_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enriched_experiences: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)
    enriched_amenities: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    photos_scraped: Mapped[list[str]] = mapped_column(JSON_VARIANT, default=list)
    outreach_status: Mapped[OutreachStatus] = mapped_column(
        SAEnum(OutreachStatus), default=OutreachStatus.not_contacted
    )
    outreach_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    auto_profile_lodge_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("lodges.id"), nullable=True)

    outreach_events = relationship("OutreachEvent", back_populates="prospect")

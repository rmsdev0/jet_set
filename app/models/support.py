from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, JSON_VARIANT


class ClaimStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class BookingPaymentType(str, enum.Enum):
    deposit = "deposit"
    full = "full"
    balance = "balance"


class BookingPaymentStatus(str, enum.Enum):
    pending = "pending"
    requires_action = "requires_action"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"
    cancelled = "cancelled"


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class LodgeOwner(BaseModel):
    __tablename__ = "lodge_owners"
    __table_args__ = (UniqueConstraint("user_id", "lodge_id", name="uq_lodge_owner_user_lodge"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    lodge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lodges.id"), index=True)

    user = relationship("User", back_populates="owned_lodges")
    lodge = relationship("Lodge", back_populates="owners")


class Claim(BaseModel):
    __tablename__ = "claims"

    lodge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lodges.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    owner_name: Mapped[str] = mapped_column(String(255))
    owner_email: Mapped[str] = mapped_column(String(255))
    owner_phone: Mapped[str] = mapped_column(String(50))
    verification_method: Mapped[str] = mapped_column(String(50))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(SAEnum(ClaimStatus), default=ClaimStatus.pending)
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    lodge = relationship("Lodge", back_populates="claims")
    user = relationship("User", back_populates="submitted_claims", foreign_keys=[user_id])
    reviewer = relationship("User", back_populates="reviewed_claims", foreign_keys=[reviewed_by_id])


class CancellationPolicy(BaseModel):
    __tablename__ = "cancellation_policies"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    refund_rules: Mapped[list[dict]] = mapped_column(JSON_VARIANT, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    lodges = relationship("Lodge", back_populates="cancellation_policy")
    bookings = relationship("Booking", back_populates="cancellation_policy")


class BookingPayment(BaseModel):
    __tablename__ = "booking_payments"

    booking_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bookings.id"), index=True)
    payment_type: Mapped[BookingPaymentType] = mapped_column(SAEnum(BookingPaymentType), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    lodge_payout: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BookingPaymentStatus] = mapped_column(
        SAEnum(BookingPaymentStatus), default=BookingPaymentStatus.pending
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)

    booking = relationship("Booking", back_populates="payments")


class ProcessedWebhookEvent(BaseModel):
    __tablename__ = "processed_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_processed_webhook_provider_event"),)

    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)


class JobQueue(BaseModel):
    __tablename__ = "job_queue"

    queue: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict] = mapped_column(JSON_VARIANT, default=dict)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.queued)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Species(BaseModel):
    __tablename__ = "species"

    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    sport_type: Mapped[str] = mapped_column(String(50), index=True)


class Destination(BaseModel):
    __tablename__ = "destinations"

    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    country: Mapped[str] = mapped_column(String(100), index=True)
    region: Mapped[str] = mapped_column(String(255), index=True)
    blurb: Mapped[str] = mapped_column(Text, default="")


class OutreachEvent(BaseModel):
    __tablename__ = "outreach_events"

    prospect_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prospects.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict | None] = mapped_column(JSON_VARIANT, nullable=True)

    prospect = relationship("Prospect", back_populates="outreach_events")

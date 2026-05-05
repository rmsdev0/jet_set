from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    deposit_paid = "deposit_paid"
    paid_in_full = "paid_in_full"
    cancelled = "cancelled"
    completed = "completed"


class SelectedPaymentType(str, enum.Enum):
    deposit = "deposit"
    full = "full"


class Booking(BaseModel):
    __tablename__ = "bookings"

    booking_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    availability_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("availability.id"), index=True)
    experience_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("experiences.id"), index=True)
    lodge_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lodges.id"), index=True)
    cancellation_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cancellation_policies.id"), nullable=True
    )
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    total_price: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_fee: Mapped[int] = mapped_column(Integer, nullable=False)
    lodge_payout: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_due_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balance_due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[BookingStatus] = mapped_column(SAEnum(BookingStatus), default=BookingStatus.pending)
    selected_payment_type: Mapped[SelectedPaymentType] = mapped_column(
        SAEnum(SelectedPaymentType), default=SelectedPaymentType.deposit, nullable=False
    )
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    special_requests: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user = relationship("User", back_populates="bookings")
    availability = relationship("Availability", back_populates="bookings")
    lodge = relationship("Lodge", back_populates="bookings")
    experience = relationship("Experience")
    review = relationship("Review", back_populates="booking", uselist=False)
    payments = relationship("BookingPayment", back_populates="booking")
    cancellation_policy = relationship("CancellationPolicy", back_populates="bookings")

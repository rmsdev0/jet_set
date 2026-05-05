from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import BookingPaymentStatus, BookingPaymentType, BookingStatus, SelectedPaymentType
from app.schemas.common import TimestampedModel


class BookingCreate(BaseModel):
    availability_id: UUID
    guest_count: int = Field(ge=1)
    special_requests: Optional[str] = None
    payment_type: SelectedPaymentType


class BookingPaymentRead(TimestampedModel):
    booking_id: UUID
    payment_type: BookingPaymentType
    amount: int
    platform_fee: int
    lodge_payout: int
    status: BookingPaymentStatus
    stripe_payment_intent_id: Optional[str] = None
    due_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None


class BookingRead(TimestampedModel):
    booking_number: str
    user_id: UUID
    availability_id: UUID
    experience_id: UUID
    lodge_id: UUID
    guest_count: int
    currency: str
    total_price: int
    platform_fee: int
    lodge_payout: int
    deposit_amount: int
    balance_due_amount: int
    balance_due_at: Optional[date] = None
    status: BookingStatus
    selected_payment_type: SelectedPaymentType
    stripe_payment_intent_id: Optional[str] = None
    special_requests: Optional[str] = None
    payments: List[BookingPaymentRead] = []


class BookingPaymentIntentResponse(BaseModel):
    booking: BookingRead
    client_secret: str


class BalancePaymentIntentResponse(BaseModel):
    booking: BookingRead
    client_secret: str


class BookingCancelResponse(BaseModel):
    booking: BookingRead
    refund_percentage: float


class BookingListItem(BaseModel):
    id: UUID
    booking_number: str
    status: BookingStatus
    guest_count: int
    total_price: int
    lodge_name: str
    experience_name: str
    trip_start: date

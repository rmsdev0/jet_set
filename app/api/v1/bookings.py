from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_booking_service_dep, get_current_user, get_db
from app.models import User
from app.schemas.booking import (
    BalancePaymentIntentResponse,
    BookingCancelResponse,
    BookingCreate,
    BookingPaymentIntentResponse,
    BookingRead,
)
from app.services.booking_service import BookingService


router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingPaymentIntentResponse)
async def create_booking(
    payload: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service_dep),
):
    booking, client_secret = await booking_service.create_booking(db, current_user, payload)
    return BookingPaymentIntentResponse(booking=BookingRead.model_validate(booking), client_secret=client_secret)


@router.get("/me", response_model=list[BookingRead])
async def list_my_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service_dep),
):
    bookings = await booking_service.list_user_bookings(db, current_user.id)
    return [BookingRead.model_validate(booking) for booking in bookings]


@router.post("/{booking_id}/cancel", response_model=BookingCancelResponse)
async def cancel_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service_dep),
):
    booking, refund_percentage = await booking_service.cancel_booking(db, booking_id, current_user)
    return BookingCancelResponse(booking=BookingRead.model_validate(booking), refund_percentage=refund_percentage)


@router.post("/{booking_id}/pay-balance", response_model=BalancePaymentIntentResponse)
async def pay_balance(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service_dep),
):
    booking, client_secret = await booking_service.create_balance_payment_intent(db, booking_id, current_user)
    return BalancePaymentIntentResponse(booking=BookingRead.model_validate(booking), client_secret=client_secret)

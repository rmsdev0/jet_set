from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.booking_service import BookingService


async def handle_payment_succeeded(db: AsyncSession, booking_service: BookingService, payment_intent_id: str) -> None:
    await booking_service.mark_payment_succeeded(db, payment_intent_id)

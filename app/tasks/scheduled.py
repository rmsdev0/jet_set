from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, BookingStatus


async def mark_completed_bookings(db: AsyncSession) -> int:
    query = select(Booking).where(
        Booking.status.in_([BookingStatus.deposit_paid, BookingStatus.paid_in_full]),
    ).options(selectinload(Booking.availability))
    bookings = list((await db.execute(query)).scalars().all())
    count = 0
    today = datetime.utcnow().date()
    for booking in bookings:
        if booking.availability.end_date < today - timedelta(days=1):
            booking.status = BookingStatus.completed
            count += 1
    await db.commit()
    return count

from __future__ import annotations

import datetime as dt

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking


async def generate_booking_number(db: AsyncSession) -> str:
    year = dt.date.today().year
    start_of_year = dt.datetime(year, 1, 1)
    statement: Select = select(func.count(Booking.id)).where(Booking.created_at >= start_of_year)
    count = (await db.execute(statement)).scalar_one()
    return f"CC-{year}-{count + 1:05d}"

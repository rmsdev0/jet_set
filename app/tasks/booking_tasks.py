from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_service import EmailService


async def send_balance_due_reminder(db: AsyncSession, email_service: EmailService, booking_id: str, email: str) -> None:
    await email_service.send_email(email, "Trip balance due", f"Booking {booking_id} has an outstanding balance.")

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.models import (
    Availability,
    AvailabilityStatus,
    Booking,
    BookingPayment,
    BookingPaymentStatus,
    BookingPaymentType,
    BookingStatus,
    CancellationPolicy,
    LodgeOwner,
    SelectedPaymentType,
    User,
)
from app.models.experience import Experience
from app.models.lodge import Lodge
from app.schemas.booking import BookingCreate
from app.services.email_service import EmailService
from app.services.job_service import JobService
from app.services.payment_service import PaymentService
from app.utils.booking import generate_booking_number
from app.utils.money import percentage_amount


DEFAULT_POLICY_RULES = [
    {"days_before": 30, "refund_percentage": 0.95},
    {"days_before": 15, "refund_percentage": 0.50},
    {"days_before": 0, "refund_percentage": 0.00},
]


class BookingService:
    def __init__(
        self,
        payment_service: PaymentService,
        job_service: JobService,
        email_service: EmailService,
        settings: Settings,
    ) -> None:
        self.payment_service = payment_service
        self.job_service = job_service
        self.email_service = email_service
        self.settings = settings

    async def create_booking(self, db: AsyncSession, current_user: User, payload: BookingCreate) -> tuple[Booking, str]:
        availability = (
            await db.execute(
                select(Availability)
                .options(selectinload(Availability.experience).selectinload(Experience.lodge))
                .where(Availability.id == payload.availability_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if availability is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability not found.")
        if availability.status != AvailabilityStatus.open:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Availability is not bookable.")
        if availability.spots_remaining < payload.guest_count:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough spots remaining.")
        if availability.start_date < date.today():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Availability window has already started.")

        experience = availability.experience
        lodge = experience.lodge
        unit_price = availability.price_override or experience.price_per_person
        if unit_price is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Experience pricing is not configured.")
        total_price = unit_price * payload.guest_count
        platform_fee = percentage_amount(total_price, self.settings.platform_fee_percentage)
        lodge_payout = total_price - platform_fee
        deposit_amount = 0
        balance_due_amount = 0
        balance_due_at = None
        initial_charge = total_price
        initial_payment_type = BookingPaymentType.full
        if payload.payment_type == SelectedPaymentType.deposit:
            deposit_amount = percentage_amount(total_price, self.settings.deposit_percentage)
            balance_due_amount = total_price - deposit_amount
            balance_due_at = max(date.today(), availability.start_date - timedelta(days=30))
            initial_charge = deposit_amount
            initial_payment_type = BookingPaymentType.deposit

        booking = Booking(
            booking_number=await generate_booking_number(db),
            user_id=current_user.id,
            availability_id=availability.id,
            experience_id=experience.id,
            lodge_id=lodge.id,
            cancellation_policy_id=lodge.cancellation_policy_id,
            guest_count=payload.guest_count,
            total_price=total_price,
            platform_fee=platform_fee,
            lodge_payout=lodge_payout,
            deposit_amount=deposit_amount,
            balance_due_amount=balance_due_amount,
            balance_due_at=balance_due_at,
            selected_payment_type=payload.payment_type,
            special_requests=payload.special_requests,
            currency=lodge.currency,
        )
        availability.spots_remaining -= payload.guest_count
        if availability.spots_remaining == 0:
            availability.status = AvailabilityStatus.full
        db.add(booking)
        await db.flush()

        initial_payment = BookingPayment(
            booking_id=booking.id,
            payment_type=initial_payment_type,
            amount=initial_charge,
            platform_fee=percentage_amount(initial_charge, self.settings.platform_fee_percentage),
            lodge_payout=initial_charge - percentage_amount(initial_charge, self.settings.platform_fee_percentage),
            status=BookingPaymentStatus.requires_action,
            due_at=datetime.now(timezone.utc),
        )
        db.add(initial_payment)

        if balance_due_amount > 0:
            db.add(
                BookingPayment(
                    booking_id=booking.id,
                    payment_type=BookingPaymentType.balance,
                    amount=balance_due_amount,
                    platform_fee=percentage_amount(balance_due_amount, self.settings.platform_fee_percentage),
                    lodge_payout=balance_due_amount - percentage_amount(balance_due_amount, self.settings.platform_fee_percentage),
                    status=BookingPaymentStatus.pending,
                    due_at=datetime.combine(balance_due_at, time(hour=9), tzinfo=timezone.utc),
                )
            )

        payment_intent = await self.payment_service.create_booking_payment(
            str(booking.id),
            initial_payment.amount,
            initial_payment.platform_fee,
            initial_payment.payment_type.value,
        )
        initial_payment.stripe_payment_intent_id = payment_intent.id
        booking.stripe_payment_intent_id = payment_intent.id
        await db.commit()
        booking = await self.get_booking(db, booking.id)
        return booking, payment_intent.client_secret

    async def get_booking(self, db: AsyncSession, booking_id) -> Booking:
        booking = (
            await db.execute(
                select(Booking)
                .options(
                    selectinload(Booking.payments),
                    selectinload(Booking.lodge),
                    selectinload(Booking.experience),
                    selectinload(Booking.availability),
                    selectinload(Booking.user),
                )
                .where(Booking.id == booking_id)
            )
        ).scalar_one_or_none()
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        return booking

    async def list_user_bookings(self, db: AsyncSession, user_id) -> list[Booking]:
        query = (
            select(Booking)
            .options(
                selectinload(Booking.lodge),
                selectinload(Booking.experience),
                selectinload(Booking.availability),
                selectinload(Booking.payments),
            )
            .where(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        )
        return list((await db.execute(query)).scalars().all())

    async def create_balance_payment_intent(self, db: AsyncSession, booking_id, current_user: User) -> tuple[Booking, str]:
        booking = await self.get_booking(db, booking_id)
        if booking.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot pay another user's booking.")
        balance_payment = next((payment for payment in booking.payments if payment.payment_type == BookingPaymentType.balance), None)
        if balance_payment is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking does not have a balance payment.")
        if balance_payment.status == BookingPaymentStatus.succeeded:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Balance has already been paid.")
        payment_intent = await self.payment_service.create_booking_payment(
            str(booking.id),
            balance_payment.amount,
            balance_payment.platform_fee,
            balance_payment.payment_type.value,
        )
        balance_payment.status = BookingPaymentStatus.requires_action
        balance_payment.stripe_payment_intent_id = payment_intent.id
        await db.commit()
        booking = await self.get_booking(db, booking.id)
        return booking, payment_intent.client_secret

    async def cancel_booking(self, db: AsyncSession, booking_id, current_user: User) -> tuple[Booking, float]:
        booking = await self.get_booking(db, booking_id)
        if booking.user_id != current_user.id and current_user.role.value != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel another user's booking.")
        if booking.status == BookingStatus.cancelled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is already cancelled.")
        availability = booking.availability
        refund_percentage = await self._resolve_refund_percentage(db, booking)
        paid_payments = [payment for payment in booking.payments if payment.status == BookingPaymentStatus.succeeded]
        if paid_payments:
            latest_payment = paid_payments[-1]
            refund_amount = int(latest_payment.amount * refund_percentage)
            if latest_payment.stripe_payment_intent_id and refund_amount > 0:
                await self.payment_service.process_refund(latest_payment.stripe_payment_intent_id, refund_amount)
            latest_payment.status = BookingPaymentStatus.refunded if refund_amount > 0 else BookingPaymentStatus.cancelled
        for payment in booking.payments:
            if payment.status in {BookingPaymentStatus.pending, BookingPaymentStatus.requires_action}:
                payment.status = BookingPaymentStatus.cancelled
        availability.spots_remaining += booking.guest_count
        availability.status = AvailabilityStatus.open
        booking.status = BookingStatus.cancelled
        booking.cancelled_at = datetime.now(timezone.utc)
        await db.commit()
        booking = await self.get_booking(db, booking.id)
        return booking, refund_percentage

    async def mark_payment_succeeded(self, db: AsyncSession, payment_intent_id: str) -> Booking:
        payment = (
            await db.execute(select(BookingPayment).where(BookingPayment.stripe_payment_intent_id == payment_intent_id))
        ).scalar_one_or_none()
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
        if payment.status == BookingPaymentStatus.succeeded:
            return await self.get_booking(db, payment.booking_id)
        payment.status = BookingPaymentStatus.succeeded
        payment.paid_at = datetime.now(timezone.utc)
        booking = await self.get_booking(db, payment.booking_id)
        if payment.payment_type in {BookingPaymentType.full, BookingPaymentType.balance}:
            booking.status = BookingStatus.paid_in_full
        else:
            booking.status = BookingStatus.deposit_paid
            await self.job_service.enqueue(
                db,
                "booking.balance_due_reminder",
                {"booking_id": str(booking.id), "email": booking.user.email},
                delay_seconds=0,
            )
        await db.commit()
        booking = await self.get_booking(db, booking.id)
        await self.email_service.send_email(
            booking.user.email,
            f"Booking {booking.booking_number} confirmed",
            "Payment received.",
            {"booking_id": str(booking.id)},
        )
        return booking

    async def mark_payment_failed(self, db: AsyncSession, payment_intent_id: str) -> Booking:
        payment = (
            await db.execute(select(BookingPayment).where(BookingPayment.stripe_payment_intent_id == payment_intent_id))
        ).scalar_one_or_none()
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found.")
        payment.status = BookingPaymentStatus.failed
        booking = await self.get_booking(db, payment.booking_id)
        if payment.payment_type in {BookingPaymentType.deposit, BookingPaymentType.full} and booking.status == BookingStatus.pending:
            booking.status = BookingStatus.cancelled
            booking.availability.spots_remaining += booking.guest_count
            booking.availability.status = AvailabilityStatus.open
        await db.commit()
        return await self.get_booking(db, booking.id)

    async def list_owned_lodge_ids(self, db: AsyncSession, user_id) -> list:
        result = await db.execute(select(LodgeOwner.lodge_id).where(LodgeOwner.user_id == user_id))
        return list(result.scalars().all())

    async def _resolve_refund_percentage(self, db: AsyncSession, booking: Booking) -> float:
        rules = DEFAULT_POLICY_RULES
        if booking.cancellation_policy_id:
            policy = await db.get(CancellationPolicy, booking.cancellation_policy_id)
            if policy and policy.refund_rules:
                rules = policy.refund_rules
        days_before_trip = (booking.availability.start_date - date.today()).days
        for rule in sorted(rules, key=lambda item: item["days_before"], reverse=True):
            if days_before_trip >= int(rule["days_before"]):
                return float(rule["refund_percentage"])
        return 0.0


def get_booking_service() -> BookingService:
    return BookingService(get_payment_service(), JobService(), get_email_service(), get_settings())

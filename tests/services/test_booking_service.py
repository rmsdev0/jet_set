from __future__ import annotations

from app.models import BookingPaymentStatus, BookingStatus, SelectedPaymentType
from app.schemas.booking import BookingCreate


async def test_create_deposit_booking_creates_balance_payment(db_session, booking_service, seeded_booking_graph):
    user = seeded_booking_graph["user"]
    availability = seeded_booking_graph["availability"]
    booking, client_secret = await booking_service.create_booking(
        db_session,
        user,
        BookingCreate(availability_id=availability.id, guest_count=2, payment_type=SelectedPaymentType.deposit),
    )
    assert booking.status == BookingStatus.pending
    assert booking.deposit_amount > 0
    assert booking.balance_due_amount > 0
    assert client_secret.startswith("pi_")
    assert len(booking.payments) == 2
    assert booking.payments[0].status == BookingPaymentStatus.requires_action


async def test_cancel_booking_restores_spots(db_session, booking_service, seeded_booking_graph):
    user = seeded_booking_graph["user"]
    availability = seeded_booking_graph["availability"]
    booking, _ = await booking_service.create_booking(
        db_session,
        user,
        BookingCreate(availability_id=availability.id, guest_count=3, payment_type=SelectedPaymentType.full),
    )
    cancelled, refund_percentage = await booking_service.cancel_booking(db_session, booking.id, user)
    assert cancelled.status == BookingStatus.cancelled
    assert refund_percentage >= 0
    await db_session.refresh(availability)
    assert availability.spots_remaining == 4

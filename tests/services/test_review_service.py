from __future__ import annotations

from app.models import BookingStatus
from app.schemas.booking import BookingCreate
from app.schemas.review import ReviewCreate


async def test_create_review_updates_lodge_aggregates(db_session, booking_service, review_service, seeded_booking_graph):
    user = seeded_booking_graph["user"]
    availability = seeded_booking_graph["availability"]
    lodge = seeded_booking_graph["lodge"]
    booking, _ = await booking_service.create_booking(
        db_session, user, BookingCreate(availability_id=availability.id, guest_count=1, payment_type="full")
    )
    booking.status = BookingStatus.completed
    await db_session.commit()
    review = await review_service.create_review(
        db_session,
        user,
        ReviewCreate(
            booking_id=booking.id,
            overall_rating=5,
            sport_rating=5,
            accommodation_rating=4,
            guide_rating=5,
            food_rating=4,
            value_rating=5,
            title="Excellent trip",
            body="Would book again.",
        ),
    )
    await db_session.refresh(lodge)
    assert review.overall_rating == 5
    assert lodge.rating_count == 1
    assert lodge.rating_avg == 5.0

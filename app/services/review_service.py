from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Booking, BookingStatus, Review, User
from app.schemas.review import ReviewCreate
from app.services.lodge_service import LodgeService


class ReviewService:
    def __init__(self, lodge_service: LodgeService) -> None:
        self.lodge_service = lodge_service

    async def create_review(self, db: AsyncSession, current_user: User, payload: ReviewCreate) -> Review:
        booking = (
            await db.execute(select(Booking).options(selectinload(Booking.review)).where(Booking.id == payload.booking_id))
        ).scalar_one_or_none()
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        if booking.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot review another user's booking.")
        if booking.status != BookingStatus.completed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only completed bookings can be reviewed.")
        if booking.review is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking already has a review.")

        review = Review(
            user_id=current_user.id,
            lodge_id=booking.lodge_id,
            booking_id=booking.id,
            overall_rating=payload.overall_rating,
            sport_rating=payload.sport_rating,
            accommodation_rating=payload.accommodation_rating,
            guide_rating=payload.guide_rating,
            food_rating=payload.food_rating,
            value_rating=payload.value_rating,
            title=payload.title,
            body=payload.body,
            photos=payload.photos or [],
            is_verified=True,
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        await self.lodge_service.recalculate_lodge_aggregates(db, booking.lodge_id)
        return review


def get_review_service() -> ReviewService:
    return ReviewService(get_lodge_service())

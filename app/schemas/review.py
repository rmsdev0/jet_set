from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedModel
from app.schemas.user import UserSummary


class ReviewCreate(BaseModel):
    booking_id: UUID
    overall_rating: int = Field(ge=1, le=5)
    sport_rating: int = Field(ge=1, le=5)
    accommodation_rating: int = Field(ge=1, le=5)
    guide_rating: int = Field(ge=1, le=5)
    food_rating: int = Field(ge=1, le=5)
    value_rating: int = Field(ge=1, le=5)
    title: str
    body: str
    photos: Optional[List[str]] = None


class ReviewRead(TimestampedModel):
    user_id: UUID
    lodge_id: UUID
    booking_id: UUID
    overall_rating: int
    sport_rating: int
    accommodation_rating: int
    guide_rating: int
    food_rating: int
    value_rating: int
    title: str
    body: str
    photos: List[str]
    is_verified: bool
    user: Optional[UserSummary] = None

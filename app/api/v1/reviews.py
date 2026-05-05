from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_review_service_dep
from app.models import User
from app.schemas.review import ReviewCreate, ReviewRead
from app.services.review_service import ReviewService


router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewRead)
async def create_review(
    payload: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    review_service: ReviewService = Depends(get_review_service_dep),
):
    review = await review_service.create_review(db, current_user, payload)
    return ReviewRead.model_validate(review)

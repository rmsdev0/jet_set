from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_lodge_admin_service
from app.schemas.common import CursorPage, CursorPageMeta
from app.schemas.lodge import LodgeDetail, LodgeSummary
from app.schemas.review import ReviewRead
from app.schemas.search import LodgeSearchParams
from app.services.lodge_service import LodgeService


router = APIRouter(prefix="/lodges", tags=["lodges"])


@router.get("", response_model=CursorPage[LodgeSummary])
async def list_lodges(
    params: LodgeSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    lodges, next_cursor = await lodge_service.search_lodges(db, params)
    items = [
        LodgeSummary.model_validate(
            {
                **lodge.__dict__,
                "primary_photo": lodge.photos[0] if lodge.photos else None,
                "is_bookable": bool(lodge.stripe_account_id),
            }
        )
        for lodge in lodges
    ]
    return CursorPage(items=items, meta=CursorPageMeta(next_cursor=next_cursor))


@router.get("/{slug}", response_model=LodgeDetail)
async def get_lodge(
    slug: str,
    db: AsyncSession = Depends(get_db),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    lodge = await lodge_service.get_lodge_by_slug(db, slug, increment_view_count=True)
    return LodgeDetail.model_validate(lodge)


@router.get("/{slug}/reviews", response_model=list[ReviewRead])
async def get_lodge_reviews(
    slug: str,
    sort: str = Query(default="newest"),
    db: AsyncSession = Depends(get_db),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    reviews = await lodge_service.get_lodge_reviews(db, slug, sort)
    return [ReviewRead.model_validate(review) for review in reviews]

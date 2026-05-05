from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_lodge_admin_service
from app.schemas.common import CursorPage, CursorPageMeta
from app.schemas.lodge import LodgeSummary
from app.schemas.search import LodgeSearchParams
from app.services.lodge_service import LodgeService


router = APIRouter(prefix="/search", tags=["search"])


@router.get("/lodges", response_model=CursorPage[LodgeSummary])
async def search_lodges(
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

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_lodge_admin_service
from app.schemas.availability import AvailabilityRead
from app.services.lodge_service import LodgeService


router = APIRouter(prefix="/experiences", tags=["experiences"])


@router.get("/{experience_id}/availability", response_model=list[AvailabilityRead])
async def get_experience_availability(
    experience_id: str,
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    windows = await lodge_service.get_experience_availability(db, experience_id, date_from, date_to)
    results = []
    for window in windows:
        effective_price = window.price_override or window.experience.price_per_person
        results.append(AvailabilityRead.model_validate({**window.__dict__, "effective_price": effective_price}))
    return results

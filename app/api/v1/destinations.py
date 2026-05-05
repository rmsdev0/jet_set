from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_lodge_admin_service
from app.services.lodge_service import LodgeService


router = APIRouter(prefix="/destinations", tags=["destinations"])


@router.get("")
async def list_destinations(
    db: AsyncSession = Depends(get_db),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    items = await lodge_service.list_destinations(db)
    return [
        {"id": str(item.id), "slug": item.slug, "name": item.name, "country": item.country, "region": item.region}
        for item in items
    ]

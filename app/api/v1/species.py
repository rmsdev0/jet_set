from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_lodge_admin_service
from app.services.lodge_service import LodgeService


router = APIRouter(prefix="/species", tags=["species"])


@router.get("")
async def list_species(
    db: AsyncSession = Depends(get_db),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    species = await lodge_service.list_species(db)
    return [{"id": str(item.id), "slug": item.slug, "name": item.name, "sport_type": item.sport_type} for item in species]

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_claim_service_dep, get_current_user, get_db
from app.models import User
from app.schemas.admin import ClaimRead, ClaimRequest
from app.services.claim_service import ClaimService


router = APIRouter(prefix="/lodges", tags=["claims"])


@router.post("/{slug}/claim", response_model=ClaimRead)
async def create_claim(
    slug: str,
    payload: ClaimRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    claim_service: ClaimService = Depends(get_claim_service_dep),
):
    claim = await claim_service.create_claim(db, slug, current_user, payload)
    return ClaimRead.model_validate(claim)

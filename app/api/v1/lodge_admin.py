from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_booking_service_dep, get_current_user, get_db, get_lodge_admin_service
from app.models import Lodge, User, UserRole
from app.schemas.availability import AvailabilityCreate, AvailabilityRead
from app.schemas.booking import BookingRead
from app.services.booking_service import BookingService
from app.services.lodge_service import LodgeService


router = APIRouter(prefix="/lodge-admin", tags=["lodge-admin"])


@router.post("/availability", response_model=list[AvailabilityRead])
async def create_availability(
    payload: AvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    if current_user.role not in {UserRole.lodge_owner, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Lodge owner access required.")
    items = await lodge_service.create_availability_windows(db, payload.experience_id, payload.windows)
    return [AvailabilityRead.model_validate(item) for item in items]


@router.get("/bookings", response_model=list[BookingRead])
async def list_lodge_bookings(
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service_dep),
    lodge_service: LodgeService = Depends(get_lodge_admin_service),
):
    if current_user.role not in {UserRole.lodge_owner, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Lodge owner access required.")
    lodge_ids = await booking_service.list_owned_lodge_ids(db, current_user.id)
    if current_user.role == UserRole.admin and not lodge_ids:
        lodge_ids = list((await db.execute(select(Lodge.id))).scalars().all())
    bookings = await lodge_service.list_lodge_bookings(db, lodge_ids, status)
    return [BookingRead.model_validate(booking) for booking in bookings]


@router.get("/payouts")
async def list_payouts(current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.lodge_owner, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Lodge owner access required.")
    return {"items": []}

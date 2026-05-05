from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.models import User, UserRole
from app.services.admin_service import AdminService, get_admin_service
from app.services.auth_service import AuthService, get_auth_service
from app.services.booking_service import BookingService, get_booking_service
from app.services.claim_service import ClaimService, get_claim_service
from app.services.lodge_service import LodgeService, get_lodge_service
from app.services.photo_service import PhotoService, get_photo_service
from app.services.review_service import ReviewService, get_review_service


async def get_db(db: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return db


async def get_current_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_debug_user: Optional[str] = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    token = authorization.split(" ", 1)[1] if authorization and authorization.startswith("Bearer ") else None
    return await auth_service.authenticate(db, request, response, token, x_debug_user)


async def get_optional_current_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_debug_user: Optional[str] = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[User]:
    token = authorization.split(" ", 1)[1] if authorization and authorization.startswith("Bearer ") else None
    return await auth_service.maybe_authenticate(db, request, response, token, x_debug_user)


def require_role(*roles: UserRole):
    async def dependency(user: User = Depends(get_current_user), auth_service: AuthService = Depends(get_auth_service)) -> User:
        auth_service.require_roles(user, *roles)
        return user

    return dependency


def get_lodge_admin_service() -> LodgeService:
    return get_lodge_service()


def get_booking_service_dep() -> BookingService:
    return get_booking_service()


def get_review_service_dep() -> ReviewService:
    return get_review_service()


def get_claim_service_dep() -> ClaimService:
    return get_claim_service()


def get_photo_service_dep() -> PhotoService:
    return get_photo_service()


def get_admin_service_dep() -> AdminService:
    return get_admin_service()

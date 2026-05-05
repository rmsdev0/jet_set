from __future__ import annotations

from typing import Optional

from app.models import UserRole
from app.schemas.common import ORMModel, TimestampedModel


class UserRead(TimestampedModel):
    auth0_id: Optional[str] = None
    email: str
    name: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole
    email_verified: bool
    has_password: bool


class UserSummary(ORMModel):
    id: str
    name: str
    avatar_url: Optional[str] = None

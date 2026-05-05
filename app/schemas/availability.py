from __future__ import annotations

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models import AvailabilityStatus
from app.schemas.common import TimestampedModel


class AvailabilityWindow(BaseModel):
    start_date: date
    end_date: date
    spots_available: int = Field(ge=1)
    price_override: Optional[int] = Field(default=None, ge=0)


class AvailabilityCreate(BaseModel):
    experience_id: UUID
    windows: List[AvailabilityWindow]


class AvailabilityRead(TimestampedModel):
    experience_id: UUID
    start_date: date
    end_date: date
    spots_total: int
    spots_remaining: int
    price_override: Optional[int] = None
    status: AvailabilityStatus
    effective_price: Optional[int] = None

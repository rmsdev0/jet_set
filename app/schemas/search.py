from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import CursorPage
from app.schemas.lodge import LodgeSummary


class LodgeSearchParams(BaseModel):
    sport_type: Optional[str] = None
    species: Optional[List[str]] = None
    country: Optional[str] = None
    region: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    price_min: Optional[int] = Field(default=None, ge=0)
    price_max: Optional[int] = Field(default=None, ge=0)
    group_size: Optional[int] = Field(default=None, ge=1)
    q: Optional[str] = None
    sort: str = "relevance"
    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)


class LodgeSearchResponse(CursorPage[LodgeSummary]):
    pass

from __future__ import annotations

from typing import List, Optional

from app.schemas.common import TimestampedModel


class ExperienceRead(TimestampedModel):
    lodge_id: str
    name: str
    description: str
    sport_type: str
    duration_days: Optional[int] = None
    max_group_size: Optional[int] = None
    price_per_person: Optional[int] = None
    price_notes: Optional[str] = None
    includes: List[str]
    season_start: Optional[int] = None
    season_end: Optional[int] = None
    photos: List[str]
    is_active: bool

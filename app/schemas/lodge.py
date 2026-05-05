from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel, TimestampedModel


class LodgeSummary(TimestampedModel):
    name: str
    slug: str
    description: str
    sport_types: List[str]
    species_targeted: List[str]
    location_country: str
    location_region: str
    primary_photo: Optional[str] = None
    rating_avg: float
    rating_count: int
    starting_price_cents: Optional[int] = None
    is_bookable: bool


class LodgeDetail(TimestampedModel):
    name: str
    slug: str
    description: str
    sport_types: List[str]
    species_targeted: List[str]
    location_country: str
    location_region: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: List[str]
    max_guests: Optional[int] = None
    photos: List[str]
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    stripe_account_id: Optional[str] = None
    is_verified: bool
    is_active: bool
    is_claimed: bool
    currency: str
    rating_avg: float
    rating_count: int
    starting_price_cents: Optional[int] = None


class LodgeCreate(BaseModel):
    name: str
    description: str = ""
    sport_types: List[str] = []
    species_targeted: List[str] = []
    location_country: str
    location_region: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amenities: List[str] = []
    max_guests: Optional[int] = None
    photos: List[str] = []
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    currency: str = "USD"


class LodgeUpdate(BaseModel):
    description: Optional[str] = None
    sport_types: Optional[List[str]] = None
    species_targeted: Optional[List[str]] = None
    amenities: Optional[List[str]] = None
    max_guests: Optional[int] = None
    photos: Optional[List[str]] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

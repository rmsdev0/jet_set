from __future__ import annotations

from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import TimestampedModel


class PlatformMetrics(BaseModel):
    total_lodges: int
    claimed_lodges: int
    unclaimed_lodges: int
    total_experiences: int
    total_bookings: int
    bookings_this_month: int
    gross_booking_volume_cents: int
    platform_revenue_cents: int
    total_sportsmen: int
    total_reviews: int
    prospect_pipeline: Dict[str, int]
    conversion_funnel: Dict[str, int]


class ClaimRequest(BaseModel):
    owner_name: str
    owner_email: str
    owner_phone: str
    verification_method: str
    message: Optional[str] = None


class ClaimDecision(BaseModel):
    approved: bool
    notes: Optional[str] = None


class ClaimRead(TimestampedModel):
    lodge_id: UUID
    user_id: UUID
    owner_name: str
    owner_email: str
    owner_phone: str
    verification_method: str
    message: Optional[str] = None
    status: str
    review_notes: Optional[str] = None


class CancellationPolicyCreate(BaseModel):
    name: str
    description: str = ""
    refund_rules: List[dict]
    is_default: bool = False


class CancellationPolicyAssign(BaseModel):
    policy_id: UUID


class CancellationPolicyRead(TimestampedModel):
    name: str
    description: str
    refund_rules: List[dict]
    is_default: bool
    is_active: bool


class UploadPresignRequest(BaseModel):
    filename: str
    content_type: str
    folder: str = "photos"


class UploadPresignResponse(BaseModel):
    object_key: str
    upload_url: str
    public_url: str

from __future__ import annotations

from typing import List, Optional

from app.models import EnrichmentStatus, OutreachStatus
from app.schemas.common import TimestampedModel


class ProspectRead(TimestampedModel):
    name: str
    website_url: Optional[str] = None
    source: str
    source_id: Optional[str] = None
    region: str
    country: str
    sport_type_guess: Optional[str] = None
    species_guess: List[str]
    contact_email: Optional[str] = None
    outreach_status: OutreachStatus
    enrichment_status: EnrichmentStatus

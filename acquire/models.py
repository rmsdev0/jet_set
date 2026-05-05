from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProspectCandidate:
    name: str
    source: str
    region: str
    country: str
    website_url: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class LodgeScrapeResult:
    prospect_id: str
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    packages: list[dict[str, Any]] = field(default_factory=list)

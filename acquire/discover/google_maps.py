from __future__ import annotations


async def discover_google_maps(region: str, sport: str) -> list[dict]:
    return [{"region": region, "sport": sport, "source": "google_maps"}]

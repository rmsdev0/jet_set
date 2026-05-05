from __future__ import annotations


async def discover_instagram(region: str, sport: str) -> list[dict]:
    return [{"region": region, "sport": sport, "source": "instagram"}]

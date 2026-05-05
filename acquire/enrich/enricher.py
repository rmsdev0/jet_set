from __future__ import annotations


async def enrich_prospect(name: str, source_data: dict) -> dict:
    return {"name": name, "summary": source_data}

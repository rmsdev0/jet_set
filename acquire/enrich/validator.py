from __future__ import annotations


def validate_enrichment_payload(payload: dict) -> bool:
    return "name" in payload

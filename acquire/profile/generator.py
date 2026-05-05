from __future__ import annotations


def generate_profile_from_prospect(prospect: dict) -> dict:
    return {"lodge": prospect.get("name"), "experiences": prospect.get("experiences", [])}

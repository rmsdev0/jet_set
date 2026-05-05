from __future__ import annotations


def normalize_name(name: str) -> str:
    return " ".join(name.lower().split())

from __future__ import annotations

import base64
import json
from typing import Any


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def decode_cursor(cursor: str) -> dict[str, Any]:
    data = base64.urlsafe_b64decode(cursor.encode("utf-8"))
    return json.loads(data.decode("utf-8"))

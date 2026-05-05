from __future__ import annotations

import asyncio


async def pause_for_rate_limit(delay_seconds: float = 1.0) -> None:
    await asyncio.sleep(delay_seconds)

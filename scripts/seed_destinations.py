from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Destination
from app.utils.slug import slugify


DESTINATIONS = [
    ("Bahamas", "Bahamas", "Out Islands", "Classic flats fishing destinations."),
    ("Cordoba", "Argentina", "Cordoba", "High-volume dove shooting."),
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        for name, country, region, blurb in DESTINATIONS:
            exists = await db.scalar(select(Destination.id).where(Destination.slug == slugify(name)))
            if not exists:
                db.add(
                    Destination(
                        slug=slugify(name),
                        name=name,
                        country=country,
                        region=region,
                        blurb=blurb,
                    )
                )
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())

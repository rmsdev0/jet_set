from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Species
from app.utils.slug import slugify


SPECIES = [
    ("bonefish", "fly_fishing"),
    ("tarpon", "fly_fishing"),
    ("permit", "fly_fishing"),
    ("mallard", "wingshooting"),
    ("pheasant", "wingshooting"),
]


async def main() -> None:
    async with AsyncSessionLocal() as db:
        for name, sport_type in SPECIES:
            exists = await db.scalar(select(Species.id).where(Species.slug == slugify(name)))
            if not exists:
                db.add(Species(slug=slugify(name), name=name.title(), sport_type=sport_type))
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())

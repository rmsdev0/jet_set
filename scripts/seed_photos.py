"""
Add Unsplash placeholder photos to seeded lodges.

Usage:
    python scripts/seed_photos.py

Safe to re-run — overwrites existing photos.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Lodge


# High-quality Unsplash photos matched to each lodge's setting.
# Using direct Unsplash CDN URLs with size parameters.
LODGE_PHOTOS: dict[str, list[str]] = {
    "silver-creek-lodge": [
        "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=1200&h=800&fit=crop",  # mountain lodge at dawn
        "https://images.unsplash.com/photo-1531299204750-f0abefc3440a?w=1200&h=800&fit=crop",  # fly fishing river
        "https://images.unsplash.com/photo-1582407947092-35f2f7a3814c?w=1200&h=800&fit=crop",  # trout stream
        "https://images.unsplash.com/photo-1587061949409-02df41d5e562?w=1200&h=800&fit=crop",  # cabin interior
        "https://images.unsplash.com/photo-1510414842594-a61c69b5ae57?w=1200&h=800&fit=crop",  # mountain landscape
    ],
    "andros-south-bonefish-club": [
        "https://images.unsplash.com/photo-1559128010-7c1ad6e1b6a5?w=1200&h=800&fit=crop",  # tropical ocean flats
        "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1200&h=800&fit=crop",  # crystal clear water
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&h=800&fit=crop",  # tropical beach
        "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=1200&h=800&fit=crop",  # tropical resort
        "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?w=1200&h=800&fit=crop",  # ocean sunset
    ],
    "estancia-los-ceibos": [
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=1200&h=800&fit=crop",  # golden field at sunset
        "https://images.unsplash.com/photo-1625244724120-1fd1d34d00f6?w=1200&h=800&fit=crop",  # luxury estancia
        "https://images.unsplash.com/photo-1464226184884-fa280b87c399?w=1200&h=800&fit=crop",  # agricultural landscape
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&h=800&fit=crop",  # fine dining
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1200&h=800&fit=crop",  # open sky landscape
    ],
    "rio-manso-lodge": [
        "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1200&h=800&fit=crop",  # patagonia mountains
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1200&h=800&fit=crop",  # mountain river valley
        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1200&h=800&fit=crop",  # pristine river
        "https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=1200&h=800&fit=crop",  # cozy lodge
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1200&h=800&fit=crop",  # misty mountain forest
    ],
    "blackwater-quail-preserve": [
        "https://images.unsplash.com/photo-1500259571355-332da5cb07aa?w=1200&h=800&fit=crop",  # pine forest trail
        "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=1200&h=800&fit=crop",  # luxury lodge exterior
        "https://images.unsplash.com/photo-1444212477490-ca407925f094?w=1200&h=800&fit=crop",  # golden hour field
        "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=1200&h=800&fit=crop",  # southern plantation style
        "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?w=1200&h=800&fit=crop",  # forest path
    ],
    "turneffe-flats": [
        "https://images.unsplash.com/photo-1540202404-a2f29016b523?w=1200&h=800&fit=crop",  # caribbean water
        "https://images.unsplash.com/photo-1530053969600-caed2596d242?w=1200&h=800&fit=crop",  # mangrove flats
        "https://images.unsplash.com/photo-1499793983394-e58fc0d6b81b?w=1200&h=800&fit=crop",  # tropical pier
        "https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=1200&h=800&fit=crop",  # belize coast
        "https://images.unsplash.com/photo-1468413253725-0d5181091126?w=1200&h=800&fit=crop",  # palm trees sunset
    ],
    "highland-sporting-estate": [
        "https://images.unsplash.com/photo-1506377585622-bedcbb027afc?w=1200&h=800&fit=crop",  # scottish highlands
        "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=1200&h=800&fit=crop",  # castle/estate
        "https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=1200&h=800&fit=crop",  # country manor
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1200&h=800&fit=crop",  # moors landscape
        "https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=1200&h=800&fit=crop",  # whisky and fireplace
    ],
    "madison-river-outfitters-lodge": [
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1200&h=800&fit=crop",  # river through forest
        "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=1200&h=800&fit=crop",  # montana sunset
        "https://images.unsplash.com/photo-1549989476-69a92fa57c36?w=1200&h=800&fit=crop",  # mountain river
        "https://images.unsplash.com/photo-1587061949409-02df41d5e562?w=1200&h=800&fit=crop",  # rustic cabin
        "https://images.unsplash.com/photo-1472396961693-142e6e269027?w=1200&h=800&fit=crop",  # elk in valley
    ],
    "laguna-blanca-lodge": [
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=1200&h=800&fit=crop",  # field at golden hour
        "https://images.unsplash.com/photo-1586375300773-8384e3e4916f?w=1200&h=800&fit=crop",  # marsh wetlands
        "https://images.unsplash.com/photo-1559128010-7c1ad6e1b6a5?w=1200&h=800&fit=crop",  # water landscape
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1200&h=800&fit=crop",  # fine dining
        "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=1200&h=800&fit=crop",  # lodge pool
    ],
    "christmas-island-outfitters": [
        "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=1200&h=800&fit=crop",  # crystal ocean
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1200&h=800&fit=crop",  # tropical beach
        "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?w=1200&h=800&fit=crop",  # ocean blue
        "https://images.unsplash.com/photo-1540202404-a2f29016b523?w=1200&h=800&fit=crop",  # reef waters
        "https://images.unsplash.com/photo-1468413253725-0d5181091126?w=1200&h=800&fit=crop",  # palm sunset
    ],
}


async def main() -> None:
    async with AsyncSessionLocal() as db:
        updated = 0
        for slug, photos in LODGE_PHOTOS.items():
            lodge = (await db.execute(select(Lodge).where(Lodge.slug == slug))).scalar_one_or_none()
            if not lodge:
                print(f"  skip  {slug} (not found)")
                continue
            lodge.photos = photos
            updated += 1
            print(f"  photos  {lodge.name} ({len(photos)} images)")
        await db.commit()

    print(f"\nDone: updated {updated} lodges with placeholder photos")


if __name__ == "__main__":
    asyncio.run(main())

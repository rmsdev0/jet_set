"""
Seed the database with realistic sample lodges, experiences, and availability
so the frontend has data to display during development.

Usage:
    python scripts/seed_sample_data.py

Re-running is safe — it skips lodges that already exist (matched by slug).
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import (
    Availability,
    AvailabilityStatus,
    Experience,
    Lodge,
)
from app.utils.slug import slugify


# ── Lodges ────────────────────────────────────────────────────────────────────

LODGES = [
    {
        "name": "Silver Creek Lodge",
        "description": (
            "Nestled along the legendary Silver Creek in central Idaho, Silver Creek Lodge "
            "offers world-class sight-fishing for trophy rainbow and brown trout. The spring-fed "
            "creek provides crystal-clear water year-round, making it one of the most technical "
            "and rewarding dry fly destinations in North America. Our intimate lodge accommodates "
            "just eight guests at a time, ensuring uncrowded water and personalized guiding."
        ),
        "sport_types": ["fly_fishing"],
        "species_targeted": ["Rainbow Trout", "Brown Trout"],
        "location_country": "United States",
        "location_region": "Idaho",
        "latitude": 43.45,
        "longitude": -114.09,
        "amenities": ["Meals Included", "Guided Fishing", "Gear Provided", "Airport Transfer", "Wi-Fi", "Bar"],
        "max_guests": 8,
        "contact_email": "book@silvercreeklodge.com",
        "contact_phone": "+1-208-555-0142",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.7,
        "rating_count": 23,
        "starting_price_cents": 65000,
    },
    {
        "name": "Andros South Bonefish Club",
        "description": (
            "Andros South sits on the southwestern tip of South Andros Island, surrounded by "
            "hundreds of square miles of pristine flats. Our guides have fished these waters for "
            "generations, putting you on bonefish, permit, and barracuda in numbers that are hard "
            "to find anywhere else in the Caribbean. The lodge blends barefoot island charm with "
            "the comforts serious anglers expect after a long day on the water."
        ),
        "sport_types": ["fly_fishing"],
        "species_targeted": ["Bonefish", "Permit", "Tarpon"],
        "location_country": "Bahamas",
        "location_region": "Andros",
        "latitude": 23.87,
        "longitude": -77.58,
        "amenities": ["Meals Included", "Guided Fishing", "Gear Provided", "Airport Transfer", "Bar", "Waterfront"],
        "max_guests": 12,
        "contact_email": "info@androssouth.com",
        "contact_phone": "+1-242-555-0198",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.9,
        "rating_count": 47,
        "starting_price_cents": 550000,
    },
    {
        "name": "Estancia Los Ceibos",
        "description": (
            "Located in the heart of Córdoba province, Estancia Los Ceibos offers the finest "
            "high-volume dove shooting in the world. With millions of eared doves roosting in the "
            "surrounding agricultural fields, a typical day produces 1,000 to 2,000 shots per gun. "
            "Between sessions, enjoy the estancia's world-class Argentine cuisine, fine Malbec, "
            "and the warm hospitality that makes Córdoba a destination unto itself."
        ),
        "sport_types": ["wingshooting"],
        "species_targeted": ["Dove"],
        "location_country": "Argentina",
        "location_region": "Córdoba",
        "latitude": -31.42,
        "longitude": -64.18,
        "amenities": ["Meals Included", "Ammunition Included", "Guided Hunting", "Airport Transfer", "Bar", "Pool", "Wi-Fi"],
        "max_guests": 16,
        "contact_email": "reservas@losceibos.com.ar",
        "contact_phone": "+54-351-555-0123",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.8,
        "rating_count": 62,
        "starting_price_cents": 450000,
    },
    {
        "name": "Rio Manso Lodge",
        "description": (
            "Deep in Argentine Patagonia, Rio Manso Lodge sits at the confluence of the Manso "
            "and Villegas rivers in the shadow of the Andes. Wade pristine freestone rivers for "
            "wild rainbow and brown trout in stunning mountain scenery. With access to over 40 miles "
            "of private water, you will rarely see another angler. The lodge itself is a hand-built "
            "timber retreat with just six rooms, a fly-tying bench, and a stone fireplace."
        ),
        "sport_types": ["fly_fishing"],
        "species_targeted": ["Rainbow Trout", "Brown Trout"],
        "location_country": "Argentina",
        "location_region": "Patagonia",
        "latitude": -41.60,
        "longitude": -71.78,
        "amenities": ["Meals Included", "Guided Fishing", "Gear Provided", "Airport Transfer", "Wi-Fi", "Bar", "Fireplace"],
        "max_guests": 12,
        "contact_email": "info@riomansolodge.com",
        "contact_phone": "+54-294-555-0456",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.6,
        "rating_count": 34,
        "starting_price_cents": 480000,
    },
    {
        "name": "Blackwater Quail Preserve",
        "description": (
            "Blackwater Quail Preserve encompasses 4,000 acres of managed longleaf pine and "
            "native grass habitat in south Georgia's quail belt. Our wild bobwhite populations "
            "are among the healthiest in the Southeast, thanks to decades of prescribed burning "
            "and habitat management. Hunt behind championship-caliber pointers from a traditional "
            "mule-drawn wagon, then retire to the clubhouse for bourbon and a farm-to-table supper."
        ),
        "sport_types": ["wingshooting"],
        "species_targeted": ["Quail"],
        "location_country": "United States",
        "location_region": "Georgia",
        "latitude": 31.12,
        "longitude": -83.95,
        "amenities": ["Meals Included", "Guided Hunting", "Dog Handling", "Ammunition Available", "Clubhouse", "Wi-Fi"],
        "max_guests": 8,
        "contact_email": "hunts@blackwaterquail.com",
        "contact_phone": "+1-229-555-0301",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.5,
        "rating_count": 18,
        "starting_price_cents": 350000,
    },
    {
        "name": "Turneffe Flats",
        "description": (
            "Turneffe Flats is Belize's premier saltwater fly fishing destination, located on "
            "Turneffe Atoll — the largest coral atoll in the Western Hemisphere. Wade firm white-sand "
            "flats for tailing bonefish, stalk permit over turtle grass, and cast to rolling tarpon "
            "along mangrove edges. With the atoll's protected lagoon system and resident fish "
            "populations, this is one of the most reliable grand slam destinations in the Caribbean."
        ),
        "sport_types": ["fly_fishing"],
        "species_targeted": ["Bonefish", "Permit", "Tarpon"],
        "location_country": "Belize",
        "location_region": "Turneffe Atoll",
        "latitude": 17.33,
        "longitude": -87.85,
        "amenities": ["Meals Included", "Guided Fishing", "Gear Provided", "Airport Transfer", "Diving Available", "Bar", "Waterfront"],
        "max_guests": 16,
        "contact_email": "reservations@turneffeflats.com",
        "contact_phone": "+501-555-0220",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.8,
        "rating_count": 56,
        "starting_price_cents": 520000,
    },
    {
        "name": "Highland Sporting Estate",
        "description": (
            "Set on 12,000 acres of heather moorland in the Scottish Highlands, the Highland "
            "Sporting Estate offers driven grouse shooting as it has been practiced for over 150 years. "
            "Walk-up days over pointers are available for smaller parties. The Victorian lodge has been "
            "sympathetically restored, with roaring fires, a malt whisky library, and a game larder "
            "that would make any sporting estate proud."
        ),
        "sport_types": ["wingshooting"],
        "species_targeted": ["Pheasant"],
        "location_country": "United Kingdom",
        "location_region": "Scottish Highlands",
        "latitude": 57.48,
        "longitude": -5.20,
        "amenities": ["Meals Included", "Guided Hunting", "Gun Room", "Dog Handling", "Bar", "Wi-Fi", "Fireplace"],
        "max_guests": 10,
        "contact_email": "enquiries@highlandsporting.co.uk",
        "contact_phone": "+44-1863-555-001",
        "is_verified": True,
        "is_claimed": False,
        "rating_avg": 4.4,
        "rating_count": 12,
        "starting_price_cents": 850000,
    },
    {
        "name": "Madison River Outfitters Lodge",
        "description": (
            "Our lodge sits just minutes from the legendary Madison River near Ennis, Montana. "
            "Float the fifty-mile riffle for wild browns and rainbows, or wade the spring creeks "
            "of the Madison Valley for technical dry-fly fishing. Fall brings the famous October "
            "caddis hatch and some of the best streamer fishing in the Rockies. The lodge is casual, "
            "the food is hearty, and the whiskey is always poured."
        ),
        "sport_types": ["fly_fishing"],
        "species_targeted": ["Rainbow Trout", "Brown Trout"],
        "location_country": "United States",
        "location_region": "Montana",
        "latitude": 45.35,
        "longitude": -111.73,
        "amenities": ["Meals Included", "Guided Fishing", "Drift Boats", "Airport Transfer", "Wi-Fi", "Bar", "Fly Shop"],
        "max_guests": 10,
        "contact_email": "book@madisonoutfitters.com",
        "contact_phone": "+1-406-555-0188",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.3,
        "rating_count": 41,
        "starting_price_cents": 55000,
    },
    {
        "name": "Laguna Blanca Lodge",
        "description": (
            "Laguna Blanca is an exclusive mixed-bag wingshooting destination in the Entre Ríos "
            "province of Argentina. Shoot perdiz, ducks, pigeons, and doves across the marshes, "
            "grasslands, and grain fields of the estancia. Between drives, cast for golden dorado "
            "in the nearby Paraná River tributaries — one of the few places on earth where you can "
            "combine world-class shooting and fishing in a single trip."
        ),
        "sport_types": ["wingshooting", "fly_fishing"],
        "species_targeted": ["Dove", "Duck", "Golden Dorado"],
        "location_country": "Argentina",
        "location_region": "Entre Ríos",
        "latitude": -32.05,
        "longitude": -59.20,
        "amenities": ["Meals Included", "Ammunition Included", "Guided Hunting", "Guided Fishing", "Airport Transfer", "Bar", "Pool"],
        "max_guests": 10,
        "contact_email": "info@lagunablancalodge.com",
        "contact_phone": "+54-343-555-0789",
        "is_verified": False,
        "is_claimed": False,
        "rating_avg": 4.1,
        "rating_count": 8,
        "starting_price_cents": 380000,
    },
    {
        "name": "Christmas Island Outfitters",
        "description": (
            "Christmas Island (Kiritimati) is the largest coral atoll on the planet and home to "
            "the densest population of bonefish anywhere. Our operation runs the south side of the "
            "island, with exclusive access to flats that see almost no fishing pressure. Beyond bones, "
            "the giant trevally fishing is world-famous — double-digit GTs cruise the channels and reef "
            "edges, ready to eat a popper or fly on every tide change."
        ),
        "sport_types": ["fly_fishing"],
        "species_targeted": ["Bonefish", "Giant Trevally"],
        "location_country": "Kiribati",
        "location_region": "Christmas Island",
        "latitude": 1.87,
        "longitude": -157.47,
        "amenities": ["Meals Included", "Guided Fishing", "Gear Provided", "Airport Transfer"],
        "max_guests": 8,
        "contact_email": "trips@christmasislandoutfitters.com",
        "contact_phone": "+686-555-0100",
        "is_verified": True,
        "is_claimed": True,
        "rating_avg": 4.6,
        "rating_count": 29,
        "starting_price_cents": 490000,
    },
]


# ── Experiences (keyed by lodge slug) ─────────────────────────────────────────

EXPERIENCES = {
    "silver-creek-lodge": [
        {
            "name": "3-Day Guided Trout Package",
            "description": "Three full days of guided fly fishing on Silver Creek and surrounding spring creeks. Includes all meals, lodging, and a complimentary dozen hand-tied flies.",
            "sport_type": "fly_fishing",
            "duration_days": 3,
            "max_group_size": 4,
            "price_per_person": 195000,
            "includes": ["Lodging", "All Meals", "Guide Service", "Flies", "Transportation"],
            "season_start": 5,
            "season_end": 10,
        },
        {
            "name": "1-Day Wade Trip",
            "description": "A single guided day on Silver Creek. Perfect for anglers passing through or wanting to test the waters before booking a longer trip.",
            "sport_type": "fly_fishing",
            "duration_days": 1,
            "max_group_size": 2,
            "price_per_person": 65000,
            "includes": ["Guide Service", "Lunch", "Flies"],
            "season_start": 5,
            "season_end": 10,
        },
    ],
    "andros-south-bonefish-club": [
        {
            "name": "6-Night Bonefish Package",
            "description": "Six nights, five days of guided bonefishing on the flats of South Andros. Includes all meals, open bar, and boat transfers from Congo Town airport.",
            "sport_type": "fly_fishing",
            "duration_days": 6,
            "max_group_size": 6,
            "price_per_person": 550000,
            "includes": ["Lodging", "All Meals", "Open Bar", "Guide Service", "Boat", "Airport Transfer"],
            "season_start": 10,
            "season_end": 6,
        },
        {
            "name": "Grand Slam Week",
            "description": "Seven nights dedicated to chasing the flats grand slam — bonefish, permit, and tarpon. We position you on the best water each day based on tides and weather.",
            "sport_type": "fly_fishing",
            "duration_days": 7,
            "max_group_size": 4,
            "price_per_person": 720000,
            "includes": ["Lodging", "All Meals", "Open Bar", "Guide Service", "Boat", "Airport Transfer"],
            "season_start": 3,
            "season_end": 7,
        },
    ],
    "estancia-los-ceibos": [
        {
            "name": "3-Day High-Volume Dove",
            "description": "Three days of high-volume dove shooting in the fields surrounding the estancia. Average 1,500 shots per day. All ammunition, bird boys, and gun cleaning included.",
            "sport_type": "wingshooting",
            "duration_days": 3,
            "max_group_size": 8,
            "price_per_person": 450000,
            "includes": ["Lodging", "All Meals", "Wine & Spirits", "Ammunition", "Gun Cleaning", "Airport Transfer"],
            "season_start": 1,
            "season_end": 12,
        },
    ],
    "rio-manso-lodge": [
        {
            "name": "5-Night Patagonia Trout",
            "description": "Five nights at the lodge with four full days of guided fishing on the Manso and Villegas rivers. Wade pristine freestone water in the shadow of the Andes.",
            "sport_type": "fly_fishing",
            "duration_days": 5,
            "max_group_size": 6,
            "price_per_person": 480000,
            "includes": ["Lodging", "All Meals", "Wine", "Guide Service", "Airport Transfer"],
            "season_start": 11,
            "season_end": 4,
        },
    ],
    "blackwater-quail-preserve": [
        {
            "name": "2-Day Quail Hunt",
            "description": "Two half-days of wild bobwhite quail hunting over championship pointers from a traditional mule-drawn wagon. Afternoon sporting clays available.",
            "sport_type": "wingshooting",
            "duration_days": 2,
            "max_group_size": 4,
            "price_per_person": 350000,
            "includes": ["Lodging", "All Meals", "Dog Handling", "Guide Service", "Sporting Clays"],
            "season_start": 11,
            "season_end": 3,
        },
    ],
    "turneffe-flats": [
        {
            "name": "7-Night Grand Slam Package",
            "description": "A full week on Turneffe Atoll, fishing for bonefish, permit, and tarpon. Includes six guided fishing days, all meals, and boat transfers from Belize City.",
            "sport_type": "fly_fishing",
            "duration_days": 7,
            "max_group_size": 6,
            "price_per_person": 520000,
            "includes": ["Lodging", "All Meals", "Guide Service", "Skiff", "Airport Transfer"],
            "season_start": 1,
            "season_end": 12,
        },
    ],
    "highland-sporting-estate": [
        {
            "name": "3-Day Driven Grouse",
            "description": "Three days of traditional driven grouse shooting on the moor. Expect 80-150 brace per day in a good season. Includes all lodging and gourmet meals at the lodge.",
            "sport_type": "wingshooting",
            "duration_days": 3,
            "max_group_size": 8,
            "price_per_person": 850000,
            "includes": ["Lodging", "All Meals", "Beaters & Pickers-up", "Gun Room", "Whisky"],
            "season_start": 8,
            "season_end": 12,
        },
    ],
    "madison-river-outfitters-lodge": [
        {
            "name": "3-Day Float Trip",
            "description": "Three days floating the Madison River in a drift boat with a seasoned guide. Target wild browns and rainbows with dries, nymphs, and streamers.",
            "sport_type": "fly_fishing",
            "duration_days": 3,
            "max_group_size": 4,
            "price_per_person": 165000,
            "includes": ["Lodging", "All Meals", "Guide Service", "Drift Boat", "Flies"],
            "season_start": 6,
            "season_end": 10,
        },
        {
            "name": "October Caddis Week",
            "description": "Five days timed to the famous October caddis hatch. Dry-fly fishing at its best — big bugs, big trout, and spectacular fall colors in the Madison Valley.",
            "sport_type": "fly_fishing",
            "duration_days": 5,
            "max_group_size": 4,
            "price_per_person": 275000,
            "includes": ["Lodging", "All Meals", "Guide Service", "Drift Boat", "Flies"],
            "season_start": 10,
            "season_end": 10,
        },
    ],
    "laguna-blanca-lodge": [
        {
            "name": "4-Day Mixed Bag",
            "description": "Four days of mixed-bag shooting — perdiz, doves, ducks, and pigeons across the estancia. Afternoons free for dorado fishing on the Paraná tributaries.",
            "sport_type": "wingshooting",
            "duration_days": 4,
            "max_group_size": 6,
            "price_per_person": 380000,
            "includes": ["Lodging", "All Meals", "Wine", "Ammunition", "Guide Service", "Airport Transfer"],
            "season_start": 4,
            "season_end": 9,
        },
    ],
    "christmas-island-outfitters": [
        {
            "name": "7-Night Bones & GTs",
            "description": "A week on Christmas Island targeting bonefish on the flats and giant trevally on the reef edges. Six guided fishing days with experienced local guides.",
            "sport_type": "fly_fishing",
            "duration_days": 7,
            "max_group_size": 6,
            "price_per_person": 490000,
            "includes": ["Lodging", "All Meals", "Guide Service", "Boat", "Airport Transfer"],
            "season_start": 1,
            "season_end": 12,
        },
    ],
}


def _build_search_document(lodge: Lodge) -> str:
    parts = [
        lodge.name,
        lodge.description or "",
        lodge.location_country or "",
        lodge.location_region or "",
        " ".join(lodge.sport_types or []),
        " ".join(lodge.species_targeted or []),
        " ".join(lodge.amenities or []),
    ]
    return " ".join(part for part in parts if part).lower()


async def main() -> None:
    async with AsyncSessionLocal() as db:
        created_lodges = 0
        created_experiences = 0
        created_availability = 0

        for lodge_data in LODGES:
            slug = slugify(lodge_data["name"])
            exists = await db.scalar(select(Lodge.id).where(Lodge.slug == slug))
            if exists:
                print(f"  skip  {lodge_data['name']} (already exists)")
                continue

            lodge = Lodge(
                name=lodge_data["name"],
                slug=slug,
                description=lodge_data["description"],
                sport_types=lodge_data["sport_types"],
                species_targeted=lodge_data["species_targeted"],
                location_country=lodge_data["location_country"],
                location_region=lodge_data["location_region"],
                latitude=lodge_data.get("latitude"),
                longitude=lodge_data.get("longitude"),
                amenities=lodge_data.get("amenities", []),
                max_guests=lodge_data.get("max_guests"),
                contact_email=lodge_data.get("contact_email"),
                contact_phone=lodge_data.get("contact_phone"),
                is_verified=lodge_data.get("is_verified", False),
                is_claimed=lodge_data.get("is_claimed", False),
                currency="USD",
                rating_avg=lodge_data.get("rating_avg", 0.0),
                rating_count=lodge_data.get("rating_count", 0),
                starting_price_cents=lodge_data.get("starting_price_cents"),
                search_document="",
            )
            lodge.search_document = _build_search_document(lodge)
            db.add(lodge)
            await db.flush()
            created_lodges += 1
            print(f"  lodge  {lodge.name} ({slug})")

            # Create experiences
            for exp_data in EXPERIENCES.get(slug, []):
                exp = Experience(
                    lodge_id=lodge.id,
                    name=exp_data["name"],
                    description=exp_data["description"],
                    sport_type=exp_data["sport_type"],
                    duration_days=exp_data.get("duration_days"),
                    max_group_size=exp_data.get("max_group_size"),
                    price_per_person=exp_data.get("price_per_person"),
                    includes=exp_data.get("includes", []),
                    season_start=exp_data.get("season_start"),
                    season_end=exp_data.get("season_end"),
                    is_active=True,
                )
                db.add(exp)
                await db.flush()
                created_experiences += 1
                print(f"    exp  {exp.name} (${exp.price_per_person / 100:.0f}/person)")

                # Create availability windows for the next 6 months
                today = date.today()
                for week_offset in range(0, 26, exp.duration_days or 7):
                    start = today + timedelta(days=week_offset * 1 + 7)  # start next week
                    end = start + timedelta(days=(exp.duration_days or 3) - 1)

                    avail = Availability(
                        experience_id=exp.id,
                        start_date=start,
                        end_date=end,
                        spots_total=exp.max_group_size or 6,
                        spots_remaining=exp.max_group_size or 6,
                        status=AvailabilityStatus.open,
                    )
                    db.add(avail)
                    created_availability += 1

        await db.commit()

    print(f"\nDone: {created_lodges} lodges, {created_experiences} experiences, {created_availability} availability windows")


if __name__ == "__main__":
    asyncio.run(main())

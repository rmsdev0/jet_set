from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, case, cast, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Availability,
    AvailabilityStatus,
    Booking,
    CancellationPolicy,
    Destination,
    Experience,
    Lodge,
    Review,
    Species,
)
from app.schemas.search import LodgeSearchParams
from app.utils.pagination import decode_cursor, encode_cursor
from app.utils.slug import slugify


class LodgeService:
    async def create_lodge(self, db: AsyncSession, name: str, **fields) -> Lodge:
        base_slug = slugify(name)
        slug = base_slug
        suffix = 1
        while await db.scalar(select(func.count()).select_from(Lodge).where(Lodge.slug == slug)):
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        lodge = Lodge(name=name, slug=slug, search_document="", **fields)
        self._update_search_document(lodge)
        db.add(lodge)
        await db.commit()
        await db.refresh(lodge)
        return lodge

    async def search_lodges(self, db: AsyncSession, params: LodgeSearchParams) -> tuple[list[Lodge], str | None]:
        query = select(Lodge).where(Lodge.is_active.is_(True))

        if params.q:
            pattern = f"%{params.q.lower()}%"
            query = query.where(func.lower(Lodge.search_document).like(pattern))

        if params.sport_type:
            query = query.where(cast(Lodge.sport_types, String).ilike(f'%"{params.sport_type}"%'))

        if params.species:
            species_filters = [cast(Lodge.species_targeted, String).ilike(f'%"{value}"%') for value in params.species]
            query = query.where(or_(*species_filters))

        if params.country:
            query = query.where(Lodge.location_country == params.country)

        if params.region:
            query = query.where(Lodge.location_region.ilike(f"%{params.region}%"))

        if params.date_from or params.date_to or params.group_size:
            availability_subquery = (
                select(Experience.lodge_id)
                .join(Availability, Availability.experience_id == Experience.id)
                .where(Availability.status == AvailabilityStatus.open)
                .where(Availability.spots_remaining > 0)
            )
            if params.date_from:
                availability_subquery = availability_subquery.where(Availability.start_date >= params.date_from)
            if params.date_to:
                availability_subquery = availability_subquery.where(Availability.end_date <= params.date_to)
            if params.group_size:
                availability_subquery = availability_subquery.where(Availability.spots_remaining >= params.group_size)
            query = query.where(Lodge.id.in_(availability_subquery))

        if params.price_min is not None:
            query = query.where(Lodge.starting_price_cents.is_not(None)).where(Lodge.starting_price_cents >= params.price_min)
        if params.price_max is not None:
            query = query.where(Lodge.starting_price_cents.is_not(None)).where(Lodge.starting_price_cents <= params.price_max)

        sort_column = Lodge.created_at
        sort_desc = True
        cursor_attr = "created_at"
        if params.sort == "price_asc":
            sort_column = func.coalesce(Lodge.starting_price_cents, 0)
            sort_desc = False
            cursor_attr = "starting_price_cents"
        elif params.sort == "price_desc":
            sort_column = func.coalesce(Lodge.starting_price_cents, 0)
            cursor_attr = "starting_price_cents"
        elif params.sort == "rating":
            sort_column = func.coalesce(Lodge.rating_avg, 0)
            cursor_attr = "rating_avg"
        elif params.sort == "newest":
            sort_column = Lodge.created_at
        elif params.q:
            sort_column = case((func.lower(Lodge.name).like(f"%{params.q.lower()}%"), 1), else_=0)
            cursor_attr = "created_at"

        if params.cursor:
            decoded = decode_cursor(params.cursor)
            cursor_value = decoded["value"]
            cursor_id = decoded["id"]
            if cursor_attr == "created_at":
                cursor_value = datetime.fromisoformat(cursor_value)
            if sort_desc:
                query = query.where(or_(sort_column < cursor_value, and_(sort_column == cursor_value, Lodge.id < cursor_id)))
            else:
                query = query.where(or_(sort_column > cursor_value, and_(sort_column == cursor_value, Lodge.id > cursor_id)))

        order = sort_column.desc() if sort_desc else sort_column.asc()
        query = query.order_by(order, Lodge.id.desc() if sort_desc else Lodge.id.asc()).limit(params.limit + 1)
        result = await db.execute(query)
        lodges = list(result.scalars().all())
        next_cursor = None
        if len(lodges) > params.limit:
            lodges = lodges[: params.limit]
            value = getattr(lodges[-1], cursor_attr)
            if isinstance(value, datetime):
                value = value.isoformat()
            next_cursor = encode_cursor({"id": str(lodges[-1].id), "value": value})
        return lodges, next_cursor

    async def get_lodge_by_slug(self, db: AsyncSession, slug: str, increment_view_count: bool = False) -> Lodge:
        query = select(Lodge).options(selectinload(Lodge.experiences)).where(Lodge.slug == slug)
        lodge = (await db.execute(query)).scalar_one_or_none()
        if lodge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lodge not found.")
        if increment_view_count:
            lodge.view_count += 1
            await db.commit()
            # Commit can leave server-managed fields like updated_at expired.
            # Refresh before serialization so response building does not trigger
            # async IO from inside Pydantic attribute access.
            await db.refresh(lodge)
        return lodge

    async def get_lodge_reviews(self, db: AsyncSession, slug: str, sort: str = "newest") -> list[Review]:
        lodge = await self.get_lodge_by_slug(db, slug)
        query = select(Review).options(selectinload(Review.user)).where(Review.lodge_id == lodge.id)
        if sort == "highest":
            query = query.order_by(Review.overall_rating.desc(), Review.created_at.desc())
        elif sort == "lowest":
            query = query.order_by(Review.overall_rating.asc(), Review.created_at.desc())
        else:
            query = query.order_by(Review.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    async def get_experience_availability(
        self, db: AsyncSession, experience_id, date_from: Optional[date] = None, date_to: Optional[date] = None
    ) -> list[Availability]:
        experience = await db.get(Experience, experience_id)
        if experience is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found.")
        query = select(Availability).where(Availability.experience_id == experience_id)
        if date_from:
            query = query.where(Availability.end_date >= date_from)
        if date_to:
            query = query.where(Availability.start_date <= date_to)
        query = query.order_by(Availability.start_date.asc())
        return list((await db.execute(query)).scalars().all())

    async def create_availability_windows(self, db: AsyncSession, experience_id, windows) -> list[Availability]:
        experience = await db.get(Experience, experience_id)
        if experience is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found.")
        created: list[Availability] = []
        for window in windows:
            overlap_query = select(Availability).where(
                Availability.experience_id == experience_id,
                Availability.start_date <= window.end_date,
                Availability.end_date >= window.start_date,
            )
            if (await db.execute(overlap_query)).scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Availability windows cannot overlap.")
            availability = Availability(
                experience_id=experience_id,
                start_date=window.start_date,
                end_date=window.end_date,
                spots_total=window.spots_available,
                spots_remaining=window.spots_available,
                price_override=window.price_override,
            )
            db.add(availability)
            created.append(availability)
        await db.commit()
        for item in created:
            await db.refresh(item)
        return created

    async def list_species(self, db: AsyncSession) -> list[Species]:
        return list((await db.execute(select(Species).order_by(Species.name.asc()))).scalars().all())

    async def list_destinations(self, db: AsyncSession) -> list[Destination]:
        return list((await db.execute(select(Destination).order_by(Destination.country.asc(), Destination.name.asc()))).scalars().all())

    async def list_lodge_bookings(self, db: AsyncSession, lodge_ids: list, status_filter: Optional[str] = None) -> list[Booking]:
        query = (
            select(Booking)
            .options(
                selectinload(Booking.lodge),
                selectinload(Booking.experience),
                selectinload(Booking.availability),
                selectinload(Booking.payments),
            )
            .where(Booking.lodge_id.in_(lodge_ids))
        )
        if status_filter:
            query = query.where(Booking.status == status_filter)
        query = query.order_by(Booking.created_at.desc())
        return list((await db.execute(query)).scalars().all())

    async def recalculate_lodge_aggregates(self, db: AsyncSession, lodge_id) -> None:
        lodge = await db.get(Lodge, lodge_id)
        if lodge is None:
            return
        rating_avg, rating_count = (
            await db.execute(select(func.avg(Review.overall_rating), func.count(Review.id)).where(Review.lodge_id == lodge_id))
        ).one()
        starting_price = (
            await db.execute(select(func.min(Experience.price_per_person)).where(Experience.lodge_id == lodge_id))
        ).scalar_one()
        lodge.rating_avg = float(rating_avg or 0.0)
        lodge.rating_count = int(rating_count or 0)
        lodge.starting_price_cents = starting_price
        self._update_search_document(lodge)
        await db.commit()

    async def get_default_cancellation_policy(self, db: AsyncSession) -> Optional[CancellationPolicy]:
        return (
            await db.execute(
                select(CancellationPolicy).where(CancellationPolicy.is_default.is_(True), CancellationPolicy.is_active.is_(True))
            )
        ).scalar_one_or_none()

    def _update_search_document(self, lodge: Lodge) -> None:
        parts = [
            lodge.name,
            lodge.description or "",
            lodge.location_country or "",
            lodge.location_region or "",
            " ".join(lodge.sport_types or []),
            " ".join(lodge.species_targeted or []),
            " ".join(lodge.amenities or []),
        ]
        lodge.search_document = " ".join(part for part in parts if part).lower()


def get_lodge_service() -> LodgeService:
    return LodgeService()

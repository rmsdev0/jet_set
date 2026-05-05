from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, CancellationPolicy, Experience, Lodge, Prospect, Review, User, UserRole
from app.schemas.admin import PlatformMetrics


class AdminService:
    async def get_metrics(self, db: AsyncSession) -> PlatformMetrics:
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        total_lodges = await db.scalar(select(func.count(Lodge.id)))
        claimed_lodges = await db.scalar(select(func.count(Lodge.id)).where(Lodge.is_claimed.is_(True)))
        total_experiences = await db.scalar(select(func.count(Experience.id)))
        total_bookings = await db.scalar(select(func.count(Booking.id)))
        bookings_this_month = await db.scalar(select(func.count(Booking.id)).where(Booking.created_at >= month_start))
        gross_booking_volume = await db.scalar(select(func.coalesce(func.sum(Booking.total_price), 0)))
        platform_revenue = await db.scalar(select(func.coalesce(func.sum(Booking.platform_fee), 0)))
        total_sportsmen = await db.scalar(select(func.count(User.id)).where(User.role == UserRole.sportsman))
        total_reviews = await db.scalar(select(func.count(Review.id)))
        prospect_rows = (await db.execute(select(Prospect.outreach_status, func.count(Prospect.id)).group_by(Prospect.outreach_status))).all()
        prospect_pipeline = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in prospect_rows}
        conversion_funnel = {
            "prospects": int(await db.scalar(select(func.count(Prospect.id))) or 0),
            "contacted": int(await db.scalar(select(func.count(Prospect.id)).where(Prospect.contact_email.is_not(None))) or 0),
            "replied": int(prospect_pipeline.get("replied", 0)),
            "onboarded": int(prospect_pipeline.get("onboarded", 0)),
        }
        return PlatformMetrics(
            total_lodges=int(total_lodges or 0),
            claimed_lodges=int(claimed_lodges or 0),
            unclaimed_lodges=int((total_lodges or 0) - (claimed_lodges or 0)),
            total_experiences=int(total_experiences or 0),
            total_bookings=int(total_bookings or 0),
            bookings_this_month=int(bookings_this_month or 0),
            gross_booking_volume_cents=int(gross_booking_volume or 0),
            platform_revenue_cents=int(platform_revenue or 0),
            total_sportsmen=int(total_sportsmen or 0),
            total_reviews=int(total_reviews or 0),
            prospect_pipeline=prospect_pipeline,
            conversion_funnel=conversion_funnel,
        )

    async def list_policies(self, db: AsyncSession) -> list[CancellationPolicy]:
        return list((await db.execute(select(CancellationPolicy).order_by(CancellationPolicy.name.asc()))).scalars().all())

    async def create_policy(self, db: AsyncSession, name: str, description: str, refund_rules: list[dict], is_default: bool) -> CancellationPolicy:
        if is_default:
            for policy in await self.list_policies(db):
                policy.is_default = False
        policy = CancellationPolicy(
            name=name,
            description=description,
            refund_rules=refund_rules,
            is_default=is_default,
            is_active=True,
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        return policy

    async def assign_policy(self, db: AsyncSession, lodge_id, policy_id) -> Lodge:
        lodge = await db.get(Lodge, lodge_id)
        policy = await db.get(CancellationPolicy, policy_id)
        if lodge is None or policy is None:
            raise ValueError("Lodge or policy not found.")
        lodge.cancellation_policy_id = policy.id
        await db.commit()
        await db.refresh(lodge)
        return lodge


def get_admin_service() -> AdminService:
    return AdminService()

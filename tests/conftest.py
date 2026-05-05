from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Availability, Base, Experience, Lodge, User, UserRole
from app.services.booking_service import BookingService
from app.services.claim_service import ClaimService
from app.services.email_service import EmailService
from app.services.job_service import JobService
from app.services.lodge_service import LodgeService
from app.services.payment_service import PaymentService
from app.services.review_service import ReviewService
from app.config import Settings


@pytest.fixture()
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture()
def settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        APP_ENV="test",
        APP_URL="http://testserver",
        API_URL="http://testserver",
    )


@pytest.fixture()
def payment_service(settings: Settings) -> PaymentService:
    return PaymentService(settings)


@pytest.fixture()
def email_service(settings: Settings) -> EmailService:
    return EmailService(settings)


@pytest.fixture()
def booking_service(payment_service: PaymentService, email_service: EmailService, settings: Settings) -> BookingService:
    return BookingService(payment_service, JobService(), email_service, settings)


@pytest.fixture()
def lodge_service() -> LodgeService:
    return LodgeService()


@pytest.fixture()
def review_service(lodge_service: LodgeService) -> ReviewService:
    return ReviewService(lodge_service)


@pytest.fixture()
def claim_service(email_service: EmailService, payment_service: PaymentService) -> ClaimService:
    return ClaimService(email_service, payment_service)


@pytest.fixture()
async def seeded_booking_graph(db_session: AsyncSession, lodge_service: LodgeService):
    user = User(auth0_id="auth0|sportsman", email="sportsman@example.com", name="Sportsman", role=UserRole.sportsman)
    owner = User(auth0_id="auth0|owner", email="owner@example.com", name="Owner", role=UserRole.sportsman)
    admin = User(auth0_id="auth0|admin", email="admin@example.com", name="Admin", role=UserRole.admin)
    db_session.add_all([user, owner, admin])
    await db_session.flush()
    lodge = await lodge_service.create_lodge(
        db_session,
        "Blue Current Lodge",
        description="Bahamas flats lodge",
        sport_types=["fly_fishing"],
        species_targeted=["bonefish"],
        location_country="Bahamas",
        location_region="Abaco",
        contact_email="owner@example.com",
    )
    experience = Experience(
        lodge_id=lodge.id,
        name="Bonefish Week",
        description="Five days on the flats",
        sport_type="fly_fishing",
        duration_days=5,
        max_group_size=4,
        price_per_person=250000,
        includes=["guide"],
        photos=[],
        is_active=True,
    )
    db_session.add(experience)
    await db_session.flush()
    availability = Availability(
        experience_id=experience.id,
        start_date=date.today() + timedelta(days=90),
        end_date=date.today() + timedelta(days=95),
        spots_total=4,
        spots_remaining=4,
    )
    db_session.add(availability)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(owner)
    await db_session.refresh(admin)
    await db_session.refresh(lodge)
    await db_session.refresh(experience)
    await db_session.refresh(availability)
    return {"user": user, "owner": owner, "admin": admin, "lodge": lodge, "experience": experience, "availability": availability}

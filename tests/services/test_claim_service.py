from __future__ import annotations

from app.models import ClaimStatus, UserRole
from app.schemas.admin import ClaimRequest


async def test_auto_approve_claim_on_email_match(db_session, claim_service, seeded_booking_graph):
    owner = seeded_booking_graph["owner"]
    lodge = seeded_booking_graph["lodge"]
    claim = await claim_service.create_claim(
        db_session,
        lodge.slug,
        owner,
        ClaimRequest(
            owner_name="Owner",
            owner_email="owner@example.com",
            owner_phone="555-1111",
            verification_method="email_match",
        ),
    )
    await db_session.refresh(owner)
    await db_session.refresh(lodge)
    assert claim.status == ClaimStatus.approved
    assert lodge.is_claimed is True
    assert owner.role == UserRole.lodge_owner

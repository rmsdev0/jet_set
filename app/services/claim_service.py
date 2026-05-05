from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Claim, ClaimStatus, Lodge, LodgeOwner, User, UserRole
from app.schemas.admin import ClaimRequest
from app.services.email_service import EmailService, get_email_service
from app.services.payment_service import PaymentService, get_payment_service


class ClaimService:
    def __init__(self, email_service: EmailService, payment_service: PaymentService) -> None:
        self.email_service = email_service
        self.payment_service = payment_service

    async def create_claim(self, db: AsyncSession, lodge_slug: str, current_user: User, payload: ClaimRequest) -> Claim:
        lodge = (await db.execute(select(Lodge).where(Lodge.slug == lodge_slug))).scalar_one_or_none()
        if lodge is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lodge not found.")
        if lodge.is_claimed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lodge has already been claimed.")

        auto_approve = bool(lodge.contact_email and lodge.contact_email.lower() == current_user.email.lower())
        claim = Claim(
            lodge_id=lodge.id,
            user_id=current_user.id,
            owner_name=payload.owner_name,
            owner_email=payload.owner_email,
            owner_phone=payload.owner_phone,
            verification_method=payload.verification_method,
            message=payload.message,
            status=ClaimStatus.approved if auto_approve else ClaimStatus.pending,
            reviewed_by_id=current_user.id if auto_approve else None,
            reviewed_at=datetime.now(timezone.utc) if auto_approve else None,
        )
        db.add(claim)
        if auto_approve:
            lodge.is_claimed = True
            db.add(LodgeOwner(user_id=current_user.id, lodge_id=lodge.id))
            if not lodge.stripe_account_id:
                account = await self.payment_service.create_lodge_account(lodge.name, current_user.email, lodge.slug)
                lodge.stripe_account_id = account.id
            if current_user.role == UserRole.sportsman:
                current_user.role = UserRole.lodge_owner
        await db.commit()
        await db.refresh(claim)
        return claim

    async def decide_claim(self, db: AsyncSession, claim_id, reviewer: User, approved: bool, notes: str | None) -> Claim:
        claim = await db.get(Claim, claim_id)
        if claim is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")
        if reviewer.role != UserRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
        lodge = await db.get(Lodge, claim.lodge_id)
        claimant = await db.get(User, claim.user_id)
        claim.status = ClaimStatus.approved if approved else ClaimStatus.rejected
        claim.review_notes = notes
        claim.reviewed_by_id = reviewer.id
        claim.reviewed_at = datetime.now(timezone.utc)
        if approved and lodge is not None and claimant is not None:
            lodge.is_claimed = True
            db.add(LodgeOwner(user_id=claim.user_id, lodge_id=claim.lodge_id))
            if claimant.role == UserRole.sportsman:
                claimant.role = UserRole.lodge_owner
            if not lodge.stripe_account_id:
                account = await self.payment_service.create_lodge_account(lodge.name, claimant.email, lodge.slug)
                lodge.stripe_account_id = account.id
            await self.email_service.send_email(
                claimant.email,
                "Your lodge claim was approved",
                f"Claim for {lodge.name} is approved.",
                {"claim_id": str(claim.id)},
            )
        await db.commit()
        await db.refresh(claim)
        return claim


def get_claim_service() -> ClaimService:
    return ClaimService(get_email_service(), get_payment_service())

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_admin_service_dep, get_claim_service_dep, get_current_user, get_db
from app.models import User, UserRole
from app.schemas.admin import (
    CancellationPolicyAssign,
    CancellationPolicyCreate,
    CancellationPolicyRead,
    ClaimDecision,
    ClaimRead,
    PlatformMetrics,
)
from app.services.admin_service import AdminService
from app.services.claim_service import ClaimService


router = APIRouter(prefix="/admin", tags=["admin"])


def _ensure_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required.")


@router.get("/metrics", response_model=PlatformMetrics)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service_dep),
):
    _ensure_admin(current_user)
    return await admin_service.get_metrics(db)


@router.post("/claims/{claim_id}/decision", response_model=ClaimRead)
async def decide_claim(
    claim_id: str,
    payload: ClaimDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    claim_service: ClaimService = Depends(get_claim_service_dep),
):
    _ensure_admin(current_user)
    claim = await claim_service.decide_claim(db, claim_id, current_user, payload.approved, payload.notes)
    return ClaimRead.model_validate(claim)


@router.get("/cancellation-policies", response_model=list[CancellationPolicyRead])
async def list_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service_dep),
):
    _ensure_admin(current_user)
    policies = await admin_service.list_policies(db)
    return [CancellationPolicyRead.model_validate(policy) for policy in policies]


@router.post("/cancellation-policies", response_model=CancellationPolicyRead)
async def create_policy(
    payload: CancellationPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service_dep),
):
    _ensure_admin(current_user)
    policy = await admin_service.create_policy(
        db, payload.name, payload.description, payload.refund_rules, payload.is_default
    )
    return CancellationPolicyRead.model_validate(policy)


@router.post("/lodges/{lodge_id}/cancellation-policy", response_model=dict)
async def assign_policy(
    lodge_id: str,
    payload: CancellationPolicyAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    admin_service: AdminService = Depends(get_admin_service_dep),
):
    _ensure_admin(current_user)
    try:
        lodge = await admin_service.assign_policy(db, lodge_id, payload.policy_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"lodge_id": str(lodge.id), "policy_id": str(lodge.cancellation_policy_id)}

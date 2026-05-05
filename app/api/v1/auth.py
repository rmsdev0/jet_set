from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.auth import (
    AuthFlowResponse,
    AuthSessionRead,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.user import UserRead
from app.services.auth_service import AuthService, get_auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthFlowResponse)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db=Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.register(db, request, response, payload)


@router.post("/login", response_model=AuthFlowResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db=Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.login(db, request, response, payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
    x_debug_user: Optional[str] = Header(default=None),
    auth_service: AuthService = Depends(get_auth_service),
):
    token = authorization.split(" ", 1)[1] if authorization and authorization.startswith("Bearer ") else None
    try:
        await auth_service.maybe_authenticate(db, request, response, token, x_debug_user)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise
    await auth_service.logout(db, request, response)
    response.status_code = status.HTTP_204_NO_CONTENT


@router.get("/session", response_model=AuthSessionRead)
async def get_session(request: Request, current_user: User = Depends(get_current_user)):
    return AuthSessionRead(
        user=UserRead.model_validate(current_user),
        auth_method=getattr(request.state, "auth_method", "session"),
    )


@router.post("/forgot-password", response_model=AuthFlowResponse, status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.forgot_password(db, request, payload)


@router.post("/reset-password", response_model=AuthFlowResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.reset_password(db, request, response, payload)


@router.post("/verify-email", response_model=AuthFlowResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.verify_email(db, request, response, payload)


@router.post("/resend-verification", response_model=AuthFlowResponse, status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    payload: ResendVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.resend_verification(db, request, payload)

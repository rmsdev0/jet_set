from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Optional

import jwt
from fastapi import HTTPException, Request, Response, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.models import User, UserOneTimeToken, UserOneTimeTokenPurpose, UserRole, UserSession
from app.schemas.auth import (
    AuthFlowResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.user import UserRead
from app.services.email_service import EmailService, get_email_service


class WindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        bucket = self._events[key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


class AuthService:
    def __init__(self, settings: Settings, email_service: EmailService) -> None:
        self.settings = settings
        self.email_service = email_service
        self.password_hasher = PasswordHash.recommended()
        self._jwks_client: Optional[jwt.PyJWKClient] = None
        self._rate_limiter = WindowRateLimiter()

    @property
    def jwks_client(self) -> jwt.PyJWKClient:
        if self._jwks_client is None:
            jwks_url = f"https://{self.settings.auth0_domain}/.well-known/jwks.json"
            self._jwks_client = jwt.PyJWKClient(jwks_url)
        return self._jwks_client

    async def authenticate(
        self,
        db: AsyncSession,
        request: Request,
        response: Response,
        token: Optional[str],
        debug_header: Optional[str] = None,
    ) -> User:
        if token:
            claims = self._decode_token(token)
            user = await self._get_or_create_user_from_auth0(db, claims)
            self._set_auth_context(request, "bearer", None)
            return user
        if request.cookies.get(self.settings.auth_session_cookie_name):
            return await self._authenticate_session(db, request, response)
        if debug_header and self.settings.app_env != "production":
            user = await self._authenticate_debug_user(db, debug_header)
            self._set_auth_context(request, "debug", None)
            return user
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    async def maybe_authenticate(
        self,
        db: AsyncSession,
        request: Request,
        response: Response,
        token: Optional[str],
        debug_header: Optional[str] = None,
    ) -> Optional[User]:
        if not token and not request.cookies.get(self.settings.auth_session_cookie_name) and not debug_header:
            return None
        return await self.authenticate(db, request, response, token, debug_header)

    async def register(
        self,
        db: AsyncSession,
        request: Request,
        response: Response,
        payload: RegisterRequest,
    ) -> AuthFlowResponse:
        self._enforce_rate_limit(f"register:ip:{self._client_ip(request)}", 5, 15 * 60, "Too many signup attempts.")
        existing = await self._get_user_by_email(db, payload.email)
        if existing is not None:
            dev_token = None
            if self.settings.auth_require_email_verification and not existing.email_verified:
                raw_token = await self._create_one_time_token(
                    db,
                    request,
                    existing,
                    UserOneTimeTokenPurpose.email_verification,
                    self.settings.auth_email_verification_ttl_seconds,
                )
                await self._send_verification_email(existing, raw_token)
                dev_token = raw_token
            elif not existing.has_password:
                dev_token = await self._create_password_reset_flow(db, request, existing)
            return AuthFlowResponse(
                message="If an account can be created or completed for that email, next steps have been sent.",
                requires_email_verification=bool(self.settings.auth_require_email_verification and not existing.email_verified),
                dev_token=self._dev_token(dev_token),
            )

        now = self._now()
        user = User(
            email=payload.email,
            name=payload.name,
            role=UserRole.sportsman,
            password_hash=self.password_hasher.hash(payload.password),
            password_set_at=now,
            email_verified_at=None if self.settings.auth_require_email_verification else now,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        if self.settings.auth_require_email_verification:
            raw_token = await self._create_one_time_token(
                db,
                request,
                user,
                UserOneTimeTokenPurpose.email_verification,
                self.settings.auth_email_verification_ttl_seconds,
            )
            await self._send_verification_email(user, raw_token)
            return AuthFlowResponse(
                message="Account created. Verify your email to continue.",
                requires_email_verification=True,
                dev_token=self._dev_token(raw_token),
            )

        user.last_login_at = now
        await db.commit()
        await self._issue_session(db, request, response, user, revoke_existing=True)
        await db.refresh(user)
        self._set_auth_context(request, "session", getattr(request.state, "current_session", None))
        return self._auth_flow_response("Account created.", user, "session")

    async def login(
        self,
        db: AsyncSession,
        request: Request,
        response: Response,
        payload: LoginRequest,
    ) -> AuthFlowResponse:
        client_ip = self._client_ip(request)
        self._enforce_rate_limit(f"login:ip:{client_ip}", 25, 15 * 60, "Too many login attempts.")
        self._enforce_rate_limit(f"login:email:{payload.email}:{client_ip}", 5, 15 * 60, "Too many login attempts.")

        user = await self._get_user_by_email(db, payload.email)
        if user is None or not user.password_hash or not self._verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
        if self.settings.auth_require_email_verification and not user.email_verified:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email verification required.")

        user.last_login_at = self._now()
        await db.commit()
        await self._issue_session(db, request, response, user, revoke_existing=True)
        await db.refresh(user)
        self._set_auth_context(request, "session", getattr(request.state, "current_session", None))
        return self._auth_flow_response("Signed in.", user, "session")

    async def logout(self, db: AsyncSession, request: Request, response: Response) -> None:
        session = getattr(request.state, "current_session", None)
        if session is not None and session.revoked_at is None:
            session.revoked_at = self._now()
            await db.commit()
        elif request.cookies.get(self.settings.auth_session_cookie_name):
            session_row = await self._get_session_by_cookie(db, request.cookies.get(self.settings.auth_session_cookie_name, ""))
            if session_row is not None and session_row.revoked_at is None:
                session_row.revoked_at = self._now()
                await db.commit()
        self._clear_auth_cookies(response)

    async def forgot_password(
        self,
        db: AsyncSession,
        request: Request,
        payload: ForgotPasswordRequest,
    ) -> AuthFlowResponse:
        client_ip = self._client_ip(request)
        self._enforce_rate_limit(f"forgot:ip:{client_ip}", 10, 60 * 60, "Too many reset attempts.")
        self._enforce_rate_limit(f"forgot:email:{payload.email}:{client_ip}", 3, 60 * 60, "Too many reset attempts.")

        user = await self._get_user_by_email(db, payload.email)
        dev_token = None
        if user is not None:
            dev_token = await self._create_password_reset_flow(db, request, user)
        return AuthFlowResponse(
            message="If an account exists for that email, password reset instructions have been sent.",
            dev_token=self._dev_token(dev_token),
        )

    async def reset_password(
        self,
        db: AsyncSession,
        request: Request,
        response: Response,
        payload: ResetPasswordRequest,
    ) -> AuthFlowResponse:
        self._enforce_rate_limit(f"reset:ip:{self._client_ip(request)}", 10, 15 * 60, "Too many password reset attempts.")
        token_row = await self._consume_one_time_token(db, payload.token, UserOneTimeTokenPurpose.password_reset)
        user = token_row.user
        now = self._now()
        user.password_hash = self.password_hasher.hash(payload.password)
        user.password_set_at = now
        user.email_verified_at = user.email_verified_at or now
        user.last_login_at = now
        await db.commit()
        await self._issue_session(db, request, response, user, revoke_existing=True)
        await db.refresh(user)
        self._set_auth_context(request, "session", getattr(request.state, "current_session", None))
        return self._auth_flow_response("Password updated.", user, "session")

    async def verify_email(
        self,
        db: AsyncSession,
        request: Request,
        response: Response,
        payload: VerifyEmailRequest,
    ) -> AuthFlowResponse:
        self._enforce_rate_limit(f"verify:ip:{self._client_ip(request)}", 20, 15 * 60, "Too many verification attempts.")
        token_row = await self._consume_one_time_token(db, payload.token, UserOneTimeTokenPurpose.email_verification)
        user = token_row.user
        user.email_verified_at = user.email_verified_at or self._now()
        user.last_login_at = self._now()
        await db.commit()
        await self._issue_session(db, request, response, user, revoke_existing=True)
        await db.refresh(user)
        self._set_auth_context(request, "session", getattr(request.state, "current_session", None))
        return self._auth_flow_response("Email verified.", user, "session")

    async def resend_verification(
        self,
        db: AsyncSession,
        request: Request,
        payload: ResendVerificationRequest,
    ) -> AuthFlowResponse:
        client_ip = self._client_ip(request)
        self._enforce_rate_limit(f"resend:ip:{client_ip}", 10, 60 * 60, "Too many verification attempts.")
        self._enforce_rate_limit(f"resend:email:{payload.email}:{client_ip}", 3, 60 * 60, "Too many verification attempts.")

        user = await self._get_user_by_email(db, payload.email)
        dev_token = None
        if user is not None and not user.email_verified:
            raw_token = await self._create_one_time_token(
                db,
                request,
                user,
                UserOneTimeTokenPurpose.email_verification,
                self.settings.auth_email_verification_ttl_seconds,
            )
            await self._send_verification_email(user, raw_token)
            dev_token = raw_token
        return AuthFlowResponse(
            message="If a verification email can be sent for that account, it has been queued.",
            dev_token=self._dev_token(dev_token),
        )

    def require_roles(self, user: User, *roles: UserRole) -> None:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")

    def _decode_token(self, token: str) -> dict[str, Any]:
        if not self.settings.auth0_domain or not self.settings.auth0_api_audience:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth0 is not configured.")
        signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
        try:
            return jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.settings.auth0_api_audience,
                issuer=f"https://{self.settings.auth0_domain}/",
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token.") from exc

    def _role_from_claims(self, claims: dict[str, Any]) -> UserRole:
        raw_roles = claims.get("https://cartridgeandcast.com/roles") or claims.get("roles") or []
        for role in raw_roles:
            if role in {member.value for member in UserRole}:
                return UserRole(role)
        return UserRole.sportsman

    async def _get_or_create_user_from_auth0(self, db: AsyncSession, claims: dict[str, Any]) -> User:
        auth0_id = claims["sub"]
        result = await db.execute(select(User).where(User.auth0_id == auth0_id))
        user = result.scalar_one_or_none()
        role = self._role_from_claims(claims)
        raw_email = claims.get("email")
        email = self._normalize_email(raw_email) if raw_email else f"{auth0_id}@placeholder.local"
        name = (claims.get("name") or email.split("@")[0]).strip()
        email_verified = bool(claims.get("email_verified"))
        if user is None and raw_email:
            existing_by_email = await self._get_user_by_email(db, email)
            if existing_by_email is not None:
                if existing_by_email.auth0_id and existing_by_email.auth0_id != auth0_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A different Auth0 identity is already linked to this account.",
                    )
                user = existing_by_email
                user.auth0_id = auth0_id
        if user is None:
            user = User(
                auth0_id=auth0_id,
                email=email,
                name=name,
                role=role,
                email_verified_at=self._now() if email_verified else None,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
        if user.email != email:
            user.email = email
        if user.name != name:
            user.name = name
        if email_verified and not user.email_verified:
            user.email_verified_at = self._now()
        await db.commit()
        await db.refresh(user)
        return user

    async def _authenticate_debug_user(self, db: AsyncSession, debug_header: str) -> User:
        try:
            payload = json.loads(debug_header)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-Debug-User header.") from exc
        auth0_id = payload["auth0_id"]
        email = self._normalize_email(payload.get("email", f"{auth0_id}@debug.local"))
        result = await db.execute(select(User).where(User.auth0_id == auth0_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = await self._get_user_by_email(db, email)
            if user is not None and user.auth0_id is None:
                user.auth0_id = auth0_id
        if user is None:
            user = User(
                auth0_id=auth0_id,
                email=email,
                name=payload.get("name", "Debug User").strip() or "Debug User",
                role=UserRole(payload.get("role", UserRole.sportsman.value)),
                email_verified_at=self._now(),
            )
            db.add(user)
        else:
            user.name = payload.get("name", user.name).strip() or user.name
            if user.role != UserRole.admin:
                user.role = UserRole(payload.get("role", user.role.value))
        await db.commit()
        await db.refresh(user)
        return user

    async def _authenticate_session(self, db: AsyncSession, request: Request, response: Response) -> User:
        raw_token = request.cookies.get(self.settings.auth_session_cookie_name)
        if not raw_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        session = await self._get_session_by_cookie(db, raw_token)
        expires_at = self._ensure_aware(session.expires_at) if session is not None else None
        if session is None or session.revoked_at is not None or expires_at <= self._now():
            self._clear_auth_cookies(response)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

        csrf_token = request.cookies.get(self.settings.auth_csrf_cookie_name)
        if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            header_name = self.settings.auth_csrf_header_name
            header_value = request.headers.get(header_name) or request.headers.get(header_name.lower())
            if not csrf_token or not header_value or csrf_token != header_value:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
            if not hmac.compare_digest(self._hash_token(csrf_token), session.csrf_hash):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")

        now = self._now()
        should_commit = False
        session.expires_at = expires_at
        if session.last_seen_at is not None:
            session.last_seen_at = self._ensure_aware(session.last_seen_at)
        if session.last_seen_at is None or (now - session.last_seen_at) >= timedelta(minutes=5):
            session.last_seen_at = now
            should_commit = True
        csrf_to_set = csrf_token
        if not csrf_to_set:
            csrf_to_set = self._generate_token()
            session.csrf_hash = self._hash_token(csrf_to_set)
            should_commit = True
        if self._should_refresh_session(session, now):
            session.expires_at = now + timedelta(seconds=self.settings.auth_session_ttl_seconds)
            self._set_auth_cookies(response, raw_token, csrf_to_set, session.expires_at)
            should_commit = True
        elif csrf_to_set != csrf_token:
            self._set_auth_cookies(response, raw_token, csrf_to_set, session.expires_at)
        if should_commit:
            await db.commit()
            await db.refresh(session)
        self._set_auth_context(request, "session", session)
        return session.user

    async def _issue_session(
        self,
        db: AsyncSession,
        request: Request,
        response: Response,
        user: User,
        *,
        revoke_existing: bool,
    ) -> UserSession:
        if revoke_existing:
            await self._revoke_user_sessions(db, user)
        raw_token = self._generate_token()
        raw_csrf = self._generate_token()
        expires_at = self._now() + timedelta(seconds=self.settings.auth_session_ttl_seconds)
        session = UserSession(
            user_id=user.id,
            token_hash=self._hash_token(raw_token),
            csrf_hash=self._hash_token(raw_csrf),
            expires_at=expires_at,
            last_seen_at=self._now(),
            created_ip=self._client_ip(request),
            created_user_agent=self._user_agent(request),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        self._set_auth_cookies(response, raw_token, raw_csrf, expires_at)
        self._set_auth_context(request, "session", session)
        return session

    async def _revoke_user_sessions(self, db: AsyncSession, user: User) -> None:
        now = self._now()
        result = await db.execute(
            select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        )
        for session in result.scalars():
            session.revoked_at = now
        await db.commit()

    async def _get_session_by_cookie(self, db: AsyncSession, raw_token: str) -> Optional[UserSession]:
        if not raw_token:
            return None
        result = await db.execute(
            select(UserSession)
            .options(selectinload(UserSession.user))
            .where(UserSession.token_hash == self._hash_token(raw_token))
        )
        return result.scalar_one_or_none()

    async def _create_password_reset_flow(self, db: AsyncSession, request: Request, user: User) -> str:
        raw_token = await self._create_one_time_token(
            db,
            request,
            user,
            UserOneTimeTokenPurpose.password_reset,
            self.settings.auth_password_reset_ttl_seconds,
        )
        await self._send_password_reset_email(user, raw_token)
        return raw_token

    async def _create_one_time_token(
        self,
        db: AsyncSession,
        request: Request,
        user: User,
        purpose: UserOneTimeTokenPurpose,
        ttl_seconds: int,
    ) -> str:
        raw_token = self._generate_token()
        token = UserOneTimeToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=self._hash_token(raw_token),
            expires_at=self._now() + timedelta(seconds=ttl_seconds),
            created_ip=self._client_ip(request),
            created_user_agent=self._user_agent(request),
        )
        db.add(token)
        await db.commit()
        return raw_token

    async def _consume_one_time_token(
        self,
        db: AsyncSession,
        raw_token: str,
        purpose: UserOneTimeTokenPurpose,
    ) -> UserOneTimeToken:
        result = await db.execute(
            select(UserOneTimeToken)
            .options(selectinload(UserOneTimeToken.user))
            .where(
                UserOneTimeToken.token_hash == self._hash_token(raw_token),
                UserOneTimeToken.purpose == purpose,
                UserOneTimeToken.consumed_at.is_(None),
            )
        )
        token_row = result.scalar_one_or_none()
        if token_row is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")
        token_row.expires_at = self._ensure_aware(token_row.expires_at)
        if token_row.expires_at <= self._now():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token.")
        token_row.consumed_at = self._now()
        await db.commit()
        await db.refresh(token_row)
        return token_row

    async def _get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == self._normalize_email(email)))
        return result.scalar_one_or_none()

    async def _send_password_reset_email(self, user: User, raw_token: str) -> None:
        reset_url = f"{self.settings.app_url.rstrip('/')}/reset-password?token={raw_token}"
        await self.email_service.send_email(
            user.email,
            "Reset your Cartridge & Cast password",
            f"<p>Use this link to reset your password:</p><p><a href=\"{reset_url}\">{reset_url}</a></p>",
            {"flow": "password_reset"},
        )

    async def _send_verification_email(self, user: User, raw_token: str) -> None:
        verify_url = f"{self.settings.app_url.rstrip('/')}/verify-email?token={raw_token}"
        await self.email_service.send_email(
            user.email,
            "Verify your Cartridge & Cast email",
            f"<p>Verify your email address:</p><p><a href=\"{verify_url}\">{verify_url}</a></p>",
            {"flow": "email_verification"},
        )

    def _set_auth_cookies(self, response: Response, raw_token: str, raw_csrf: str, expires_at: datetime) -> None:
        max_age = max(1, int((expires_at - self._now()).total_seconds()))
        response.set_cookie(
            key=self.settings.auth_session_cookie_name,
            value=raw_token,
            max_age=max_age,
            httponly=True,
            secure=self.settings.auth_cookie_secure,
            samesite=self.settings.auth_cookie_samesite,
            path="/",
        )
        response.set_cookie(
            key=self.settings.auth_csrf_cookie_name,
            value=raw_csrf,
            max_age=max_age,
            httponly=False,
            secure=self.settings.auth_cookie_secure,
            samesite=self.settings.auth_cookie_samesite,
            path="/",
        )

    def _clear_auth_cookies(self, response: Response) -> None:
        response.delete_cookie(self.settings.auth_session_cookie_name, path="/")
        response.delete_cookie(self.settings.auth_csrf_cookie_name, path="/")

    def _should_refresh_session(self, session: UserSession, now: datetime) -> bool:
        remaining = session.expires_at - now
        return remaining <= timedelta(seconds=self.settings.auth_session_ttl_seconds // 2)

    def _auth_flow_response(self, message: str, user: User, auth_method: str) -> AuthFlowResponse:
        return AuthFlowResponse(
            message=message,
            user=UserRead.model_validate(user),
            auth_method=auth_method,
        )

    def _set_auth_context(self, request: Request, auth_method: str, session: Optional[UserSession]) -> None:
        request.state.auth_method = auth_method
        request.state.current_session = session

    def _enforce_rate_limit(self, key: str, limit: int, window_seconds: int, detail: str) -> None:
        if not self._rate_limiter.allow(key, limit, window_seconds):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _user_agent(self, request: Request) -> Optional[str]:
        return request.headers.get("user-agent")

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return bool(self.password_hasher.verify(password, password_hash))
        except Exception:
            return False

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()

    def _dev_token(self, raw_token: Optional[str]) -> Optional[str]:
        if raw_token and self.settings.app_env != "production":
            return raw_token
        return None

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    return AuthService(get_settings(), get_email_service())

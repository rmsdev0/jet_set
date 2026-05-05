from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    sportsman = "sportsman"
    lodge_owner = "lodge_owner"
    admin = "admin"


class User(BaseModel):
    __tablename__ = "users"

    auth0_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.sportsman, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    owned_lodges = relationship("LodgeOwner", back_populates="user")
    submitted_claims = relationship("Claim", back_populates="user", foreign_keys="Claim.user_id")
    reviewed_claims = relationship("Claim", back_populates="reviewer", foreign_keys="Claim.reviewed_by_id")
    sessions = relationship("UserSession", back_populates="user")
    one_time_tokens = relationship("UserOneTimeToken", back_populates="user")

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

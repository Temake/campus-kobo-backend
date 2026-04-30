import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class UserStatus(str, enum.Enum):
    pending_verification = "pending_verification"
    active = "active"
    suspended = "suspended"
    deleted = "deleted"


class AuthProvider(str, enum.Enum):
    email = "email"
    phone = "phone"
    google = "google"
    apple = "apple"


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class VerificationPurpose(str, enum.Enum):
    signup = "signup"
    change_email = "change_email"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    provider: Mapped[AuthProvider] = mapped_column(Enum(AuthProvider), default=AuthProvider.email, nullable=False)
    provider_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.pending_verification, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_pin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pin_hash: Mapped[str | None] = mapped_column(String(255))
    biometric_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hide_balance: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_analytics: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    admin_two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_two_factor_secret: Mapped[str | None] = mapped_column(String(255))
    admin_ip_allowlist: Mapped[str | None] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(255))
    device_id: Mapped[str | None] = mapped_column(String(255))
    platform: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sessions")


class AdminAuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_audit_logs"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[str | None] = mapped_column(Text)

    admin_user: Mapped["User"] = relationship()


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (UniqueConstraint("token", name="uq_refresh_tokens_token"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class EmailVerificationCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "email_verification_codes"
    __table_args__ = (
        Index("ix_email_verification_codes_lookup", "user_id", "purpose", "consumed_at"),
        Index("ix_email_verification_codes_email_lookup", "sent_to_email", "purpose", "consumed_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    purpose: Mapped[VerificationPurpose] = mapped_column(Enum(VerificationPurpose), nullable=False)
    sent_to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)

    user: Mapped["User"] = relationship()

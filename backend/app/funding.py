from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.main import Base


class DepositIntent(Base):
    __tablename__ = "deposit_intents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    provider_reference: Mapped[Optional[str]] = mapped_column(String(160), unique=True, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(16), default="USDT")
    network: Mapped[str] = mapped_column(String(32))
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(28, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    deposit_address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    provider_reference: Mapped[Optional[str]] = mapped_column(String(160), unique=True, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(16), default="USDT")
    network: Mapped[str] = mapped_column(String(32))
    address: Mapped[str] = mapped_column(String(256))
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ProviderEvent(Base):
    __tablename__ = "provider_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(80))
    event_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="received")
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String
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

class BlockchainCursor(Base):
    __tablename__ = "blockchain_cursors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    network: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    cursor: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class BlockchainTransfer(Base):
    __tablename__ = "blockchain_transfers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    network: Mapped[str] = mapped_column(String(32), index=True)
    tx_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    log_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    block_number: Mapped[int] = mapped_column(BigInteger, index=True)
    token_contract: Mapped[str] = mapped_column(String(128))
    from_address: Mapped[str] = mapped_column(String(256))
    to_address: Mapped[str] = mapped_column(String(256))
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    confirmations: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="detected", index=True)
    deposit_intent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("deposit_intents.id"), nullable=True, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    credited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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

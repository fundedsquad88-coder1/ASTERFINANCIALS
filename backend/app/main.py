import hashlib
import json
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, EmailStr, Field
from pwdlib import PasswordHash
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, create_engine, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aster-dev.db")
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))
COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "").split(",") if x.strip()]
CSRF_HEADER = "X-Aster-CSRF"
password_hash = PasswordHash.recommended()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="active")
    kyc_status: Mapped[str] = mapped_column(String(32), default="unverified")
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SessionToken(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Wallet(Base):
    __tablename__ = "wallets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    available: Mapped[Decimal] = mapped_column(Numeric(28, 8), default=0)
    invested: Mapped[Decimal] = mapped_column(Numeric(28, 8), default=0)
    pending: Mapped[Decimal] = mapped_column(Numeric(28, 8), default=0)

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(128))
    endpoint: Mapped[str] = mapped_column(String(120))
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[str] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("user_id", "key", "endpoint", name="uq_idempotency_user_key_endpoint"),)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    currency: Mapped[str] = mapped_column(String(16), default="USDT")
    reference: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(16), default="USDT")
    status: Mapped[str] = mapped_column(String(24), default="posted")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class LedgerPosting(Base):
    __tablename__ = "ledger_postings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("ledger_transactions.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    account: Mapped[str] = mapped_column(String(64), index=True)
    debit: Mapped[Decimal] = mapped_column(Numeric(28, 8), default=0)
    credit: Mapped[Decimal] = mapped_column(Numeric(28, 8), default=0)
    currency: Mapped[str] = mapped_column(String(16), default="USDT")

def post_double_entry(dbs: Session, *, user_id: int, reference: str, amount: Decimal, debit_account: str, credit_account: str, currency: str = "USDT") -> None:
    if amount <= 0:
        raise ValueError("Ledger amount must be positive")
    tx = LedgerTransaction(reference=reference, currency=currency, status="posted")
    dbs.add(tx)
    dbs.flush()
    dbs.add(LedgerPosting(transaction_id=tx.id, user_id=user_id, account=debit_account, debit=amount, credit=Decimal("0"), currency=currency))
    dbs.add(LedgerPosting(transaction_id=tx.id, user_id=user_id, account=credit_account, debit=Decimal("0"), credit=amount, currency=currency))

def transfer_wallet_balance(dbs: Session, *, user_id: int, amount: Decimal, source: str, destination: str, reference: str) -> None:
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    if not w:
        raise HTTPException(404, "Wallet not found")
    balances = ledger_account_balances(dbs, user_id)
    available = balances.get(source, Decimal("0"))
    if available < amount:
        raise HTTPException(409, "Insufficient available balance")
    post_double_entry(dbs, user_id=user_id, reference=reference, amount=amount,
                      debit_account=destination, credit_account=source)


class AutoInvest(Base):
    __tablename__ = "autoinvest"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    strategy: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    duration_weeks: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))



class ValuationSource(Base):
    __tablename__ = "valuation_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy: Mapped[str] = mapped_column(String(40), unique=True)
    provider: Mapped[str] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

class StrategyValuation(Base):
    __tablename__ = "strategy_valuations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    autoinvest_id: Mapped[int] = mapped_column(ForeignKey("autoinvest.id"), index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    source: Mapped[str] = mapped_column(String(40), default="server")
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(1000))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))



class AuthToken(Base):
    __tablename__ = "auth_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    referred_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    bonus_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.1500"))
    pending_bonus: Mapped[Decimal] = mapped_column(Numeric(28, 8), default=0)
    paid_bonus: Mapped[Decimal] = mapped_column(Numeric(28, 8), default=0)
    status: Mapped[str] = mapped_column(String(24), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    metadata_json: Mapped[str] = mapped_column(String(4000), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

from app.funding import DepositIntent, WithdrawalRequest, ProviderEvent

if os.getenv("ASTER_SKIP_CREATE_ALL", "false").lower() != "true":
    Base.metadata.create_all(engine)

# Production deployments use versioned migrations; create_all is only a local bootstrap.

app = FastAPI(title="Aster Financials API", version="0.4.0")
if ALLOWED_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
                       allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"],
                       allow_headers=["Content-Type","X-Aster-CSRF"])
allowed_hosts = [x.strip() for x in os.getenv("ALLOWED_HOSTS", "").split(",") if x.strip()]
if allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    username: Optional[str] = Field(default=None, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=32)
    country: Optional[str] = Field(default=None, max_length=80)
    referral_code: Optional[str] = None

class ProfileUpdateIn(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    phone: Optional[str] = Field(default=None, max_length=32)
    country: Optional[str] = Field(default=None, max_length=80)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AutoInvestIn(BaseModel):
    strategy: str = Field(pattern="^(Core Crypto|Global FX|core-crypto|global-fx)$")
    amount: Decimal = Field(gt=0)
    duration_weeks: int = Field(ge=1, le=104)


MAX_VALUATION_AGE_SECONDS = int(os.getenv("MAX_VALUATION_AGE_SECONDS", "300"))

def validate_valuation(value: Decimal, as_of: datetime) -> None:
    if value < Decimal("0"):
        raise HTTPException(400, "Valuation cannot be negative")
    age = (datetime.now(timezone.utc) - utc_datetime(as_of)).total_seconds()
    if age < -30:
        raise HTTPException(400, "Valuation timestamp is in the future")
    if age > MAX_VALUATION_AGE_SECONDS:
        raise HTTPException(409, "Valuation is stale")


def db():
    with SessionLocal() as s:
        yield s

def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def utc_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

def issue_session(response: Response, dbs: Session, user_id: int) -> str:
    raw = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    dbs.add(SessionToken(user_id=user_id, token_hash=digest(raw), csrf_hash=digest(csrf),
                         expires_at=datetime.now(timezone.utc)+timedelta(hours=SESSION_TTL_HOURS)))
    dbs.commit()
    response.set_cookie("__Host-AsterSession", raw, httponly=True, secure=COOKIE_SECURE, samesite="lax",
                        path="/", max_age=SESSION_TTL_HOURS*3600)
    response.set_cookie("AsterCSRF", csrf, httponly=False, secure=COOKIE_SECURE, samesite="lax",
                        path="/", max_age=SESSION_TTL_HOURS*3600)
    return csrf

def current_user(session_cookie: Optional[str] = Cookie(default=None, alias="__Host-AsterSession"),
                 dbs: Session = Depends(db)):
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required")
    row = dbs.scalar(select(SessionToken).where(SessionToken.token_hash==digest(session_cookie)))
    if not row or utc_datetime(row.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = dbs.get(User, row.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=403, detail="Account unavailable")
    return user

def require_idempotency_key(
    key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if not key or len(key) < 16 or len(key) > 128:
        raise HTTPException(status_code=400, detail="A valid Idempotency-Key is required")
    return key

def require_csrf(session_cookie: Optional[str] = Cookie(default=None, alias="__Host-AsterSession"),
                 csrf_cookie: Optional[str] = Cookie(default=None, alias="AsterCSRF"),
                 csrf_header: Optional[str] = Header(default=None, alias=CSRF_HEADER),
                 dbs: Session = Depends(db)):
    if not session_cookie or not csrf_cookie or not csrf_header or not hmac.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    row = dbs.scalar(select(SessionToken).where(SessionToken.token_hash==digest(session_cookie)))
    if not row or not hmac.compare_digest(row.csrf_hash, digest(csrf_cookie)):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

@app.get("/health")
def health(): return {"ok": True, "service": "aster-api"}

class EmailVerifyIn(BaseModel):
    token: str = Field(min_length=20, max_length=256)

@app.post("/v1/auth/email-verification/request")
def email_verification_request(user: User = Depends(current_user), dbs: Session = Depends(db)):
    if user.status != "active": raise HTTPException(403, "Account unavailable")
    raw = make_token()
    dbs.add(EmailVerification(user_id=user.id, token_hash=digest(raw), expires_at=datetime.now(timezone.utc)+timedelta(hours=24)))
    dbs.add(AuditEvent(user_id=user.id, event_type="email_verification_requested"))
    dbs.commit()
    result = {"ok": True, "message": "Verification instructions are queued for delivery."}
    if os.getenv("ASTER_EXPOSE_DEV_VERIFY_TOKEN", "false").lower() == "true": result["dev_token"] = raw
    return result

@app.post("/v1/auth/email-verification/confirm")
def email_verification_confirm(body: EmailVerifyIn, user: User = Depends(current_user), dbs: Session = Depends(db)):
    row = dbs.scalar(select(EmailVerification).where(EmailVerification.token_hash == digest(body.token), EmailVerification.user_id == user.id))
    if not row or row.verified_at or utc_datetime(row.expires_at) < datetime.now(timezone.utc): raise HTTPException(400, "Invalid or expired verification token")
    row.verified_at = datetime.now(timezone.utc)
    user.email_verified = True
    dbs.add(AuditEvent(user_id=user.id, event_type="email_verified")); dbs.commit()
    return {"ok": True, "email_verified": True}

@app.get("/v1/production/status")
def production_status():
    return {
        "api": "ready",
        "database": "configured" if os.getenv("DATABASE_URL") else "local-development-fallback",
        "funding_provider": bool(os.getenv("ASTER_FUNDING_PROVIDER") or os.getenv("ASTER_FUNDING_WEBHOOK_SECRET")),
        "email_provider": bool(os.getenv("ASTER_EMAIL_PROVIDER")),
        "auto_invest_execution_provider": bool(os.getenv("ASTER_AUTOINVEST_PROVIDER")),
        "valuation_provider": bool(os.getenv("ASTER_VALUATION_PROVIDER")),
        "push_provider": bool(os.getenv("ASTER_PUSH_PROVIDER")),
        "note": "Features without a configured provider remain fail-closed; the API never fabricates settlement or performance."
    }

@app.get("/v1/admin/treasury/summary")
def admin_treasury_summary(x_aster_admin_key: Optional[str] = Header(default=None, alias="X-Aster-Admin-Key"), dbs: Session = Depends(db)):
    expected = os.getenv("ASTER_ADMIN_API_KEY", "")
    if len(expected) < 32 or not x_aster_admin_key or not hmac.compare_digest(expected, x_aster_admin_key): raise HTTPException(403, "Admin authorization required")
    deposits = dbs.execute(select(DepositIntent.status, func.count(DepositIntent.id)).group_by(DepositIntent.status)).all()
    withdrawals = dbs.execute(select(WithdrawalRequest.status, func.count(WithdrawalRequest.id)).group_by(WithdrawalRequest.status)).all()
    events = dbs.execute(select(ProviderEvent.status, func.count(ProviderEvent.id)).group_by(ProviderEvent.status)).all()
    return {"deposits": {s:int(n) for s,n in deposits}, "withdrawals": {s:int(n) for s,n in withdrawals}, "provider_events": {s:int(n) for s,n in events}, "treasury_networks": ["BEP20","TRC20"]}


@app.post("/v1/auth/register", status_code=201)
def register(body: RegisterIn, response: Response, dbs: Session = Depends(db)):
    email = body.email.lower()
    if dbs.scalar(select(User).where(User.email==email)):
        raise HTTPException(409, "Account already exists")
    if body.username and dbs.scalar(select(User).where(User.username == body.username.lower())):
        raise HTTPException(409, "Username already exists")
    user = User(email=email, username=body.username.lower() if body.username else None,
                first_name=body.first_name.strip() if body.first_name else None,
                phone=body.phone.strip() if body.phone else None,
                country=body.country.strip() if body.country else None,
                email_verified=False, password_hash=password_hash.hash(body.password),
                referral_code="ASTER-"+secrets.token_hex(4).upper())
    dbs.add(user); dbs.flush()
    if body.referral_code:
        referrer = dbs.scalar(select(User).where(User.referral_code == body.referral_code.strip().upper()))
        if referrer and referrer.id != user.id: dbs.add(Referral(referrer_user_id=referrer.id, referred_user_id=user.id))
    dbs.add(Wallet(user_id=user.id))
    dbs.commit()
    csrf = issue_session(response, dbs, user.id)
    return {"id": user.id, "email": user.email, "email_verified": user.email_verified, "csrf_token": csrf}

@app.post("/v1/auth/login")
def login(body: LoginIn, response: Response, dbs: Session = Depends(db)):
    user = dbs.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not password_hash.verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    csrf = issue_session(response, dbs, user.id)
    return {"id": user.id, "email": user.email, "kyc_status": user.kyc_status, "csrf_token": csrf}

@app.post("/v1/auth/logout")
def logout(response: Response, session_cookie: Optional[str] = Cookie(default=None, alias="__Host-AsterSession"),
           dbs: Session = Depends(db)):
    if session_cookie:
        row = dbs.scalar(select(SessionToken).where(SessionToken.token_hash==digest(session_cookie)))
        if row: dbs.delete(row); dbs.commit()
    response.delete_cookie("__Host-AsterSession", path="/")
    response.delete_cookie("AsterCSRF", path="/")
    return {"ok": True}

@app.get("/v1/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "username": user.username, "first_name": user.first_name,
            "phone": user.phone, "country": user.country, "status": user.status,
            "email_verified": user.email_verified, "referral_code": user.referral_code,
            "created_at": user.created_at, "last_login_at": user.last_login_at}

@app.patch("/v1/profile")
def update_profile(body: ProfileUpdateIn, user: User = Depends(current_user), dbs: Session = Depends(db),
                   _: None = Depends(require_csrf)):
    if body.username and body.username.lower() != (user.username or ""):
        if dbs.scalar(select(User).where(User.username == body.username.lower(), User.id != user.id)):
            raise HTTPException(409, "Username already exists")
        user.username = body.username.lower()
    if body.first_name is not None: user.first_name = body.first_name.strip()
    if body.phone is not None: user.phone = body.phone.strip() or None
    if body.country is not None: user.country = body.country.strip() or None
    dbs.add(AuditEvent(user_id=user.id, event_type="profile_updated"))
    dbs.commit()
    return {"ok": True, "profile": {"username": user.username, "first_name": user.first_name,
                                    "phone": user.phone, "country": user.country, "email": user.email,
                                    "email_verified": user.email_verified}}


class DepositIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=24)

class WithdrawalIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=24)
    address: str = Field(min_length=10, max_length=256)
    amount: Decimal = Field(gt=0)



class PasswordResetIn(BaseModel):
    email: EmailStr

class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=12, max_length=128)

def make_token() -> str:
    return secrets.token_urlsafe(48)

def create_auth_token(dbs: Session, user_id: int, purpose: str, ttl_hours: int = 1) -> str:
    raw = make_token()
    dbs.add(AuthToken(user_id=user_id, token_hash=digest(raw), purpose=purpose, expires_at=datetime.now(timezone.utc)+timedelta(hours=ttl_hours)))
    return raw

@app.post("/v1/auth/password-reset/request")
def password_reset_request(body: PasswordResetIn, dbs: Session = Depends(db)):
    user = dbs.scalar(select(User).where(User.email == body.email.lower()))
    if not user:
        return {"ok": True, "message": "If the account exists, reset instructions will be sent."}
    token = create_auth_token(dbs, user.id, "password_reset", 1)
    dbs.add(AuditEvent(user_id=user.id, event_type="password_reset_requested", metadata_json=json.dumps({"delivery":"provider_required"})))
    dbs.commit()
    if os.getenv("ASTER_EXPOSE_DEV_RESET_TOKEN", "false").lower() == "true":
        return {"ok": True, "dev_token": token}
    return {"ok": True, "message": "If the account exists, reset instructions will be sent."}

@app.post("/v1/auth/password-reset/confirm")
def password_reset_confirm(body: PasswordResetConfirmIn, response: Response, dbs: Session = Depends(db)):
    row = dbs.scalar(select(AuthToken).where(AuthToken.token_hash == digest(body.token), AuthToken.purpose == "password_reset"))
    if not row or row.used_at or utc_datetime(row.expires_at) < datetime.now(timezone.utc): raise HTTPException(400, "Invalid or expired reset token")
    user = dbs.get(User, row.user_id)
    if not user or user.status != "active": raise HTTPException(403, "Account unavailable")
    user.password_hash = password_hash.hash(body.password); row.used_at = datetime.now(timezone.utc)
    dbs.query(SessionToken).filter(SessionToken.user_id == user.id).delete(synchronize_session=False)
    dbs.add(AuditEvent(user_id=user.id, event_type="password_reset_completed")); dbs.commit()
    response.delete_cookie("__Host-AsterSession", path="/"); response.delete_cookie("AsterCSRF", path="/")
    return {"ok": True}

@app.get("/v1/security/sessions")
def security_sessions(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(SessionToken).where(SessionToken.user_id == user.id).order_by(SessionToken.created_at.desc())).all()
    return [{"id":r.id,"created_at":r.created_at,"expires_at":r.expires_at} for r in rows]

@app.delete("/v1/security/sessions/{session_id}")
def revoke_session(session_id: int, user: User = Depends(current_user), dbs: Session = Depends(db), _: None = Depends(require_csrf)):
    row = dbs.scalar(select(SessionToken).where(SessionToken.id == session_id, SessionToken.user_id == user.id))
    if not row: raise HTTPException(404, "Session not found")
    dbs.delete(row); dbs.add(AuditEvent(user_id=user.id, event_type="session_revoked", metadata_json=json.dumps({"session_id":session_id}))); dbs.commit()
    return {"ok": True}

@app.get("/v1/referrals")
def referrals(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(Referral).where(Referral.referrer_user_id == user.id).order_by(Referral.id.desc())).all()
    return {"code":user.referral_code,"rate":"15%","count":len(rows),"pending_bonus":str(sum((r.pending_bonus for r in rows),Decimal("0"))),"paid_bonus":str(sum((r.paid_bonus for r in rows),Decimal("0"))),"referrals":[{"id":r.id,"referred_user_id":r.referred_user_id,"status":r.status,"pending_bonus":str(r.pending_bonus),"paid_bonus":str(r.paid_bonus)} for r in rows]}

@app.get("/v1/notifications")
def notifications(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(100)).all()
    return [{"id":n.id,"title":n.title,"body":n.body,"read":n.read,"created_at":n.created_at} for n in rows]

@app.post("/v1/notifications/{notification_id}/read")
def mark_notification_read(notification_id:int,user:User=Depends(current_user),dbs:Session=Depends(db),_:None=Depends(require_csrf)):
    n=dbs.scalar(select(Notification).where(Notification.id==notification_id,Notification.user_id==user.id))
    if not n: raise HTTPException(404,"Notification not found")
    n.read=True; dbs.commit(); return {"ok":True}

@app.get("/v1/kyc/status")
def kyc_status(user: User = Depends(current_user)):
    return {"status": "not_required", "next_action": None, "note": "Identity verification is not enabled in this Aster account stage."}

@app.get("/v1/wallet")
def wallet(user: User = Depends(current_user), dbs: Session = Depends(db)):
    w = dbs.scalar(select(Wallet).where(Wallet.user_id==user.id))
    return {"available": str(w.available), "invested": str(w.invested), "pending": str(w.pending), "currency": "USDT"}


@app.get("/v1/transactions/summary")
def transactions_summary(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(LedgerEntry).where(LedgerEntry.user_id==user.id).order_by(LedgerEntry.id.desc()).limit(100)).all()
    posted = [r for r in rows if r.status=="posted"]
    credits = sum((r.amount for r in posted if r.amount > 0), Decimal("0"))
    debits = sum((-r.amount for r in posted if r.amount < 0), Decimal("0"))
    return {"count":len(rows),"posted_credits":str(credits),"posted_debits":str(debits),"currency":"USDT"}
@app.get("/v1/transactions")
def transactions(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(LedgerEntry).where(LedgerEntry.user_id==user.id).order_by(LedgerEntry.id.desc()).limit(100)).all()
    return [{"id":r.id,"kind":r.kind,"amount":str(r.amount),"currency":r.currency,"reference":r.reference,"status":r.status,"created_at":r.created_at} for r in rows]

@app.get("/v1/autoinvest/strategies")
def strategies():
    return {"strategies":[
        {"id":"core-crypto","name":"Core Crypto","type":"crypto","status":"available"},
        {"id":"global-fx","name":"Global FX","type":"fx","status":"available"}]}






def ledger_account_balances(dbs: Session, user_id: int) -> dict[str, Decimal]:
    rows = dbs.execute(
        select(LedgerPosting.account, func.coalesce(func.sum(LedgerPosting.debit), 0), func.coalesce(func.sum(LedgerPosting.credit), 0))
        .where(LedgerPosting.user_id == user_id)
        .group_by(LedgerPosting.account)
    ).all()
    return {account: Decimal(str(debits)) - Decimal(str(credits)) for account, debits, credits in rows}

@app.post("/v1/autoinvest")
def create_autoinvest(body: AutoInvestIn, user: User = Depends(current_user), dbs: Session = Depends(db),
                      _: None = Depends(require_csrf), idem: str = Depends(require_idempotency_key)):
    existing = dbs.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id == user.id, IdempotencyKey.key == idem, IdempotencyKey.endpoint == "/v1/autoinvest"))
    if existing:
        import json
        return json.loads(existing.response_body)
    try:
        strategy_name = {"core-crypto":"Core Crypto","global-fx":"Global FX"}.get(body.strategy, body.strategy)
        reference = "AI-" + secrets.token_hex(6).upper()
        transfer_wallet_balance(dbs, user_id=user.id, amount=body.amount,
                                source="user.available", destination="user.invested", reference=reference)
        w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
        w.available -= body.amount
        w.invested += body.amount
        strategy = AutoInvest(user_id=user.id, strategy=strategy_name, amount=body.amount,
                              duration_weeks=body.duration_weeks, status="active")
        dbs.add(strategy)
        dbs.add(LedgerEntry(user_id=user.id, kind="autoinvest_debit", amount=-body.amount,
                            reference=reference, status="posted"))
        dbs.flush()
        result = {"id": strategy.id, "strategy": strategy.strategy, "amount": str(strategy.amount),
                  "duration_weeks": strategy.duration_weeks, "status": strategy.status}
        import json
        dbs.add(IdempotencyKey(user_id=user.id, key=idem, endpoint="/v1/autoinvest",
                               response_status=201, response_body=json.dumps(result)))
        dbs.commit()
        return result
    except HTTPException:
        dbs.rollback()
        raise



@app.get("/v1/autoinvest/active")
def active_autoinvest(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(AutoInvest).where(AutoInvest.user_id == user.id).order_by(AutoInvest.id.desc())).all()
    return [{"id":r.id,"strategy":r.strategy,"amount":str(r.amount),"duration_weeks":r.duration_weeks,"status":r.status,"created_at":r.created_at} for r in rows]

@app.post("/v1/autoinvest/{autoinvest_id}/pause")
def pause_autoinvest(autoinvest_id:int,user:User=Depends(current_user),dbs:Session=Depends(db),_:None=Depends(require_csrf)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==autoinvest_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Auto-Invest not found")
    if row.status != "active": raise HTTPException(409,"Only active strategies can be paused")
    row.status="paused"; dbs.add(Notification(user_id=user.id,title="Auto-Invest paused",body=f"{row.strategy} has been paused.")); dbs.commit()
    return {"id":row.id,"status":row.status}

@app.post("/v1/autoinvest/{autoinvest_id}/resume")
def resume_autoinvest(autoinvest_id:int,user:User=Depends(current_user),dbs:Session=Depends(db),_:None=Depends(require_csrf)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==autoinvest_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Auto-Invest not found")
    if row.status != "paused": raise HTTPException(409,"Only paused strategies can be resumed")
    row.status="active"; dbs.add(Notification(user_id=user.id,title="Auto-Invest resumed",body=f"{row.strategy} is active again.")); dbs.commit()
    return {"id":row.id,"status":row.status}

@app.post("/v1/autoinvest/{autoinvest_id}/release")
def release_autoinvest(autoinvest_id:int,user:User=Depends(current_user),dbs:Session=Depends(db),_:None=Depends(require_csrf),idem:str=Depends(require_idempotency_key)):
    existing=dbs.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id==user.id,IdempotencyKey.key==idem,IdempotencyKey.endpoint==f"/v1/autoinvest/{autoinvest_id}/release"))
    if existing: return json.loads(existing.response_body)
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==autoinvest_id,AutoInvest.user_id==user.id).with_for_update())
    if not row: raise HTTPException(404,"Auto-Invest not found")
    if row.status not in ("active","paused"): raise HTTPException(409,"Strategy cannot be released")
    reference="AIR-"+secrets.token_hex(6).upper()
    transfer_wallet_balance(dbs,user_id=user.id,amount=row.amount,source="user.invested",destination="user.available",reference=reference)
    w=dbs.scalar(select(Wallet).where(Wallet.user_id==user.id).with_for_update()); w.invested-=row.amount; w.available+=row.amount
    row.status="released"
    dbs.add(LedgerEntry(user_id=user.id,kind="autoinvest_release",amount=row.amount,reference=reference,status="posted"))
    dbs.add(Notification(user_id=user.id,title="Funds released",body=f"{row.strategy} principal returned to your available balance."))
    result={"id":row.id,"status":row.status,"released_amount":str(row.amount)}
    dbs.add(IdempotencyKey(user_id=user.id,key=idem,endpoint=f"/v1/autoinvest/{autoinvest_id}/release",response_status=200,response_body=json.dumps(result)))
    dbs.commit(); return result

@app.get("/v1/portfolio")
def portfolio(user: User = Depends(current_user), dbs: Session = Depends(db)):
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    count = dbs.scalar(select(func.count(AutoInvest.id)).where(AutoInvest.user_id == user.id, AutoInvest.status == "active")) or 0
    return {"currency":"USDT","available":str(w.available),"invested":str(w.invested),
            "total":str(w.available + w.invested),"active":str(count),"strategy_count":int(count)}

@app.get("/v1/ledger/integrity")
def ledger_integrity(user: User = Depends(current_user), dbs: Session = Depends(db)):
    tx_ids = dbs.scalars(select(LedgerTransaction.id)).all()
    checked = 0
    unbalanced = []
    for tx_id in tx_ids:
        debits = dbs.scalar(select(func.coalesce(func.sum(LedgerPosting.debit), 0)).where(LedgerPosting.transaction_id == tx_id))
        credits = dbs.scalar(select(func.coalesce(func.sum(LedgerPosting.credit), 0)).where(LedgerPosting.transaction_id == tx_id))
        checked += 1
        if Decimal(str(debits)) != Decimal(str(credits)):
            unbalanced.append(tx_id)
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    balances = ledger_account_balances(dbs, user.id)
    wallet_available = w.available if w else Decimal("0")
    wallet_invested = w.invested if w else Decimal("0")
    wallet_pending = w.pending if w else Decimal("0")
    expected_available = balances.get("user.available", Decimal("0"))
    expected_invested = balances.get("user.invested", Decimal("0"))
    expected_pending = balances.get("user.pending", Decimal("0"))
    wallet_mismatches = {
        "available": str((wallet_available - expected_available).normalize()),
        "invested": str((wallet_invested - expected_invested).normalize()),
        "pending": str((wallet_pending - expected_pending).normalize()),
    }
    wallet_balanced = all(Decimal(v) == Decimal("0") for v in wallet_mismatches.values())
    return {"currency":"USDT","checked_transactions":checked,"balanced":not unbalanced,
            "unbalanced_transaction_ids":unbalanced[:20],"wallet_balanced":wallet_balanced,
            "wallet_mismatches":wallet_mismatches}

@app.get("/v1/portfolio/valuation-status")
def valuation_status(user: User = Depends(current_user), dbs: Session = Depends(db)):
    sources = dbs.scalars(select(ValuationSource).order_by(ValuationSource.strategy.asc())).all()
    return {"sources":[{"strategy":s.strategy,"provider":s.provider,"enabled":s.enabled,"last_sync_at":s.last_sync_at,"last_error":s.last_error} for s in sources]}

@app.get("/v1/portfolio/performance")
def portfolio_performance(user: User = Depends(current_user), dbs: Session = Depends(db)):
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    rows = dbs.scalars(select(LedgerEntry).where(LedgerEntry.user_id == user.id).order_by(LedgerEntry.id.asc()).limit(500)).all()
    deposits = sum((r.amount for r in rows if r.kind == "deposit" and r.status == "posted"), Decimal("0"))
    releases = sum((r.amount for r in rows if r.kind == "autoinvest_release" and r.status == "posted"), Decimal("0"))
    invested_debits = sum((-r.amount for r in rows if r.kind == "autoinvest_debit" and r.status == "posted"), Decimal("0"))
    net_contributed = deposits + releases
    current_total = (w.available + w.invested) if w else Decimal("0")
    realized = current_total - net_contributed
    return {
        "currency":"USDT",
        "available":str(w.available if w else Decimal("0")),
        "invested":str(w.invested if w else Decimal("0")),
        "total":str(current_total),
        "net_contributed":str(net_contributed),
        "realized_unpriced_change":str(realized),
        "valuation_status":"unpriced",
        "ledger_autoinvest_debits":str(invested_debits),
        "note":"Performance is unpriced until a real strategy valuation feed is connected. No return is inferred from wallet balances."
    }



from app.funding_routes import router as funding_router
app.include_router(funding_router)

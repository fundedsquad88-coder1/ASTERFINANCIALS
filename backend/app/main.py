import hashlib
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
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, create_engine, select
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

class AutoInvest(Base):
    __tablename__ = "autoinvest"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    strategy: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    duration_weeks: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(1000))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)

app = FastAPI(title="Aster Financials API", version="0.2.0")
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
    referral_code: Optional[str] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AutoInvestIn(BaseModel):
    strategy: str = Field(pattern="^(Core Crypto|Global FX)$")
    amount: Decimal = Field(gt=0)
    duration_weeks: int = Field(ge=1, le=104)

def db():
    with SessionLocal() as s:
        yield s

def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def issue_session(response: Response, dbs: Session, user_id: int):
    raw = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    dbs.add(SessionToken(user_id=user_id, token_hash=digest(raw), csrf_hash=digest(csrf),
                         expires_at=datetime.now(timezone.utc)+timedelta(hours=SESSION_TTL_HOURS)))
    dbs.commit()
    response.set_cookie("__Host-AsterSession", raw, httponly=True, secure=COOKIE_SECURE, samesite="lax",
                        path="/", max_age=SESSION_TTL_HOURS*3600)
    response.set_cookie("AsterCSRF", csrf, httponly=False, secure=COOKIE_SECURE, samesite="lax",
                        path="/", max_age=SESSION_TTL_HOURS*3600)

def current_user(session_cookie: Optional[str] = Cookie(default=None, alias="__Host-AsterSession"),
                 dbs: Session = Depends(db)):
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Authentication required")
    row = dbs.scalar(select(SessionToken).where(SessionToken.token_hash==digest(session_cookie)))
    if not row or row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = dbs.get(User, row.user_id)
    if not user or user.status != "active":
        raise HTTPException(status_code=403, detail="Account unavailable")
    return user

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

@app.post("/v1/auth/register", status_code=201)
def register(body: RegisterIn, response: Response, dbs: Session = Depends(db)):
    email = body.email.lower()
    if dbs.scalar(select(User).where(User.email==email)):
        raise HTTPException(409, "Account already exists")
    user = User(email=email, password_hash=password_hash.hash(body.password),
                referral_code="ASTER-"+secrets.token_hex(4).upper())
    dbs.add(user); dbs.flush()
    dbs.add(Wallet(user_id=user.id))
    dbs.commit()
    issue_session(response, dbs, user.id)
    return {"id": user.id, "email": user.email, "kyc_status": user.kyc_status}

@app.post("/v1/auth/login")
def login(body: LoginIn, response: Response, dbs: Session = Depends(db)):
    user = dbs.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not password_hash.verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    issue_session(response, dbs, user.id)
    return {"id": user.id, "email": user.email, "kyc_status": user.kyc_status}

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
    return {"id": user.id, "email": user.email, "status": user.status, "kyc_status": user.kyc_status, "referral_code": user.referral_code}


class DepositIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=24)

class WithdrawalIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=24)
    address: str = Field(min_length=10, max_length=256)
    amount: Decimal = Field(gt=0)

@app.get("/v1/kyc/status")
def kyc_status(user: User = Depends(current_user)):
    return {"status": user.kyc_status, "next_action": None if user.kyc_status == "verified" else "verification_required"}

@app.post("/v1/wallet/deposits", status_code=503)
def create_deposit(_: DepositIn, user: User = Depends(current_user), __: None = Depends(require_csrf)):
    raise HTTPException(503, "Deposit provider is not configured")

@app.post("/v1/wallet/withdrawals", status_code=503)
def create_withdrawal(_: WithdrawalIn, user: User = Depends(current_user), __: None = Depends(require_csrf)):
    raise HTTPException(503, "Withdrawal provider is not configured")

@app.get("/v1/wallet")
def wallet(user: User = Depends(current_user), dbs: Session = Depends(db)):
    w = dbs.scalar(select(Wallet).where(Wallet.user_id==user.id))
    return {"available": str(w.available), "invested": str(w.invested), "pending": str(w.pending), "currency": "USDT"}

@app.get("/v1/transactions")
def transactions(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(LedgerEntry).where(LedgerEntry.user_id==user.id).order_by(LedgerEntry.id.desc()).limit(100)).all()
    return [{"id":r.id,"kind":r.kind,"amount":str(r.amount),"currency":r.currency,"reference":r.reference,"status":r.status,"created_at":r.created_at} for r in rows]

@app.get("/v1/autoinvest/strategies")
def strategies():
    return {"strategies":[
        {"id":"core-crypto","name":"Core Crypto","type":"crypto","status":"available"},
        {"id":"global-fx","name":"Global FX","type":"fx","status":"available"}]}

@app.get("/v1/autoinvest")
def active_autoinvest(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows=dbs.scalars(select(AutoInvest).where(AutoInvest.user_id==user.id).order_by(AutoInvest.id.desc())).all()
    return [{"id":r.id,"strategy":r.strategy,"amount":str(r.amount),"duration_weeks":r.duration_weeks,"status":r.status,"created_at":r.created_at} for r in rows]

@app.post("/v1/autoinvest", status_code=201)
def create_autoinvest(body: AutoInvestIn, user: User = Depends(current_user), _: None = Depends(require_csrf), dbs: Session = Depends(db)):
    if body.amount < Decimal("10"): raise HTTPException(400, "Minimum investment is $10")
    w=dbs.scalar(select(Wallet).where(Wallet.user_id==user.id))
    if not w or w.available < body.amount: raise HTTPException(409, "Insufficient available balance")
    w.available -= body.amount; w.invested += body.amount
    strategy=AutoInvest(user_id=user.id,strategy=body.strategy,amount=body.amount,duration_weeks=body.duration_weeks)
    dbs.add(strategy)
    dbs.add(LedgerEntry(user_id=user.id,kind="autoinvest_debit",amount=-body.amount,reference="AI-"+secrets.token_hex(6).upper(),status="posted"))
    dbs.commit()
    return {"id":strategy.id,"status":strategy.status}

@app.post("/v1/autoinvest/{strategy_id}/pause")
def pause_autoinvest(strategy_id:int,user:User=Depends(current_user),_:None=Depends(require_csrf),dbs:Session=Depends(db)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==strategy_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Strategy not found")
    if row.status!="active": raise HTTPException(409,"Strategy is not active")
    row.status="paused"; dbs.commit()
    return {"id":row.id,"status":row.status}

@app.get("/v1/notifications")
def notifications(user:User=Depends(current_user),dbs:Session=Depends(db)):
    rows=dbs.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.id.desc()).limit(50)).all()
    return [{"id":n.id,"title":n.title,"body":n.body,"read":n.read,"created_at":n.created_at} for n in rows]

@app.get("/v1/referrals")
def referrals(user:User=Depends(current_user)):
    return {"code":user.referral_code,"rate":"15%","invited":0,"active":0,"earned":"0","pending":"0"}

@app.get("/v1/security/sessions")
def sessions(user:User=Depends(current_user),dbs:Session=Depends(db)):
    rows=dbs.scalars(select(SessionToken).where(SessionToken.user_id==user.id).order_by(SessionToken.id.desc())).all()
    return [{"id":r.id,"created_at":r.created_at,"expires_at":r.expires_at} for r in rows]

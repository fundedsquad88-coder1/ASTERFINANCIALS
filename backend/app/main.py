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
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, create_engine, select
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

class AutoInvest(Base):
    __tablename__ = "autoinvest"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    strategy: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    duration_weeks: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


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

Base.metadata.create_all(engine)

app = FastAPI(title="Aster Financials API", version="0.3.0")
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
    csrf = issue_session(response, dbs, user.id)
    return {"id": user.id, "email": user.email, "kyc_status": user.kyc_status, "csrf_token": csrf}

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


@app.get("/v1/portfolio/performance")
def portfolio_performance(user: User = Depends(current_user), dbs: Session = Depends(db)):
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    rows = dbs.scalars(select(AutoInvest).where(AutoInvest.user_id == user.id)).all()
    valuations = []
    for strategy in rows:
        latest = dbs.scalar(select(StrategyValuation).where(StrategyValuation.autoinvest_id == strategy.id).order_by(StrategyValuation.id.desc()))
        valuations.append(latest.value if latest else strategy.amount)
    strategy_value = sum(valuations, Decimal("0"))
    total = (w.available if w else Decimal("0")) + strategy_value
    contributed = sum((r.amount for r in dbs.scalars(select(LedgerEntry).where(LedgerEntry.user_id==user.id, LedgerEntry.kind=="autoinvest_debit", LedgerEntry.status=="posted")).all()), Decimal("0"))
    return {
        "currency":"USDT",
        "available":str(w.available if w else Decimal("0")),
        "invested":str(strategy_value),
        "total":str(total),
        "cost_basis":str(contributed),
        "unrealized_pnl":str(strategy_value-contributed),
        "valuation_status":"priced" if all(dbs.scalar(select(StrategyValuation).where(StrategyValuation.autoinvest_id==s.id).order_by(StrategyValuation.id.desc())) for s in rows) else "unpriced"
    }

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
        "ledger_autoinvest_debits":str(invested_debits),
        "note":"Performance is unpriced until a real strategy valuation feed is connected."
    }

@app.get("/v1/portfolio")
def portfolio(user: User = Depends(current_user), dbs: Session = Depends(db)):
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    rows = dbs.scalars(select(AutoInvest).where(AutoInvest.user_id == user.id).order_by(AutoInvest.id.desc())).all()
    active = [r for r in rows if r.status == "active"]
    paused = [r for r in rows if r.status == "paused"]
    return {
        "currency": "USDT",
        "available": str(w.available if w else Decimal("0")),
        "invested": str(w.invested if w else Decimal("0")),
        "pending": str(w.pending if w else Decimal("0")),
        "strategy_count": len(rows),
        "active_count": len(active),
        "paused_count": len(paused),
        "strategies": [{"id":r.id,"strategy":r.strategy,"amount":str(r.amount),"duration_weeks":r.duration_weeks,"status":r.status,"created_at":r.created_at} for r in rows],
    }

@app.get("/v1/autoinvest")
def active_autoinvest(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows=dbs.scalars(select(AutoInvest).where(AutoInvest.user_id==user.id).order_by(AutoInvest.id.desc())).all()
    return [{"id":r.id,"strategy":r.strategy,"amount":str(r.amount),"duration_weeks":r.duration_weeks,"status":r.status,"created_at":r.created_at} for r in rows]

@app.post("/v1/autoinvest", status_code=201)
def create_autoinvest(
    body: AutoInvestIn,
    user: User = Depends(current_user),
    _: None = Depends(require_csrf),
    idempotency_key: str = Depends(require_idempotency_key),
    dbs: Session = Depends(db),
):
    prior = dbs.scalar(select(IdempotencyKey).where(
        IdempotencyKey.user_id == user.id,
        IdempotencyKey.key == idempotency_key,
        IdempotencyKey.endpoint == "/v1/autoinvest",
    ))
    if prior:
        return Response(content=prior.response_body, status_code=prior.response_status, media_type="application/json")

    if body.amount < Decimal("10"):
        raise HTTPException(400, "Minimum investment is $10")
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    if not w or w.available < body.amount:
        raise HTTPException(409, "Insufficient available balance")

    w.available -= body.amount
    w.invested += body.amount
    strategy = AutoInvest(user_id=user.id, strategy=body.strategy, amount=body.amount, duration_weeks=body.duration_weeks)
    dbs.add(strategy)
    dbs.flush()
    dbs.add(LedgerEntry(user_id=user.id, kind="autoinvest_debit", amount=-body.amount,
                        reference="AI-"+secrets.token_hex(6).upper(), status="posted"))
    payload = {"id": strategy.id, "status": strategy.status}
    import json
    dbs.add(IdempotencyKey(user_id=user.id, key=idempotency_key, endpoint="/v1/autoinvest",
                           response_status=201, response_body=json.dumps(payload)))
    dbs.commit()
    return payload



class ValuationIn(BaseModel):
    value: Decimal = Field(ge=0)

@app.post("/v1/autoinvest/{strategy_id}/valuation")
def set_strategy_valuation(strategy_id:int, body:ValuationIn, user:User=Depends(current_user), _:None=Depends(require_csrf), dbs:Session=Depends(db)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==strategy_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Strategy not found")
    valuation=StrategyValuation(autoinvest_id=row.id,value=body.value,source="server",as_of=datetime.now(timezone.utc))
    dbs.add(valuation); dbs.commit()
    return {"strategy_id":row.id,"value":str(valuation.value),"as_of":valuation.as_of,"source":valuation.source}

@app.get("/v1/autoinvest/{strategy_id}/valuation")
def get_strategy_valuation(strategy_id:int,user:User=Depends(current_user),dbs:Session=Depends(db)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==strategy_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Strategy not found")
    valuation=dbs.scalar(select(StrategyValuation).where(StrategyValuation.autoinvest_id==row.id).order_by(StrategyValuation.id.desc()))
    if not valuation: return {"strategy_id":row.id,"status":"unpriced","value":str(row.amount),"as_of":None,"source":None}
    return {"strategy_id":row.id,"status":"priced","value":str(valuation.value),"as_of":valuation.as_of,"source":valuation.source}

@app.get("/v1/autoinvest/{strategy_id}")
def autoinvest_detail(strategy_id:int,user:User=Depends(current_user),dbs:Session=Depends(db)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==strategy_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Strategy not found")
    return {"id":row.id,"strategy":row.strategy,"amount":str(row.amount),"duration_weeks":row.duration_weeks,
            "status":row.status,"created_at":row.created_at}

@app.post("/v1/autoinvest/{strategy_id}/cancel")
def cancel_autoinvest(strategy_id:int,user:User=Depends(current_user),_:None=Depends(require_csrf),dbs:Session=Depends(db)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==strategy_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Strategy not found")
    if row.status=="cancelled": raise HTTPException(409,"Strategy is already cancelled")
    w=dbs.scalar(select(Wallet).where(Wallet.user_id==user.id))
    if not w: raise HTTPException(409,"Wallet not found")
    w.invested -= row.amount
    w.available += row.amount
    row.status="cancelled"
    dbs.add(LedgerEntry(user_id=user.id,kind="autoinvest_release",amount=row.amount,
                        reference="AIR-"+secrets.token_hex(6).upper(),status="posted"))
    dbs.commit()
    return {"id":row.id,"status":row.status,"released_amount":str(row.amount)}

@app.post("/v1/autoinvest/{strategy_id}/resume")
def resume_autoinvest(strategy_id:int,user:User=Depends(current_user),_:None=Depends(require_csrf),dbs:Session=Depends(db)):
    row=dbs.scalar(select(AutoInvest).where(AutoInvest.id==strategy_id,AutoInvest.user_id==user.id))
    if not row: raise HTTPException(404,"Strategy not found")
    if row.status!="paused": raise HTTPException(409,"Strategy is not paused")
    row.status="active"; dbs.commit()
    return {"id":row.id,"status":row.status}

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

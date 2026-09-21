import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.funding import DepositIntent, ProviderEvent, WithdrawalRequest
from app.main import User, Wallet, LedgerEntry, IdempotencyKey, current_user, db, require_csrf, require_idempotency_key, transfer_wallet_balance, post_double_entry

router = APIRouter()

class DepositCreateIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)

class WithdrawalCreateIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)
    address: str = Field(min_length=10, max_length=256)
    amount: Decimal = Field(gt=0)

class ProviderWebhookIn(BaseModel):
    event_id: str = Field(min_length=8, max_length=200)
    event_type: str = Field(min_length=3, max_length=80)
    provider_reference: str = Field(min_length=3, max_length=160)
    status: str = Field(pattern="^(confirmed|failed|reversed)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)

def provider_name():
    value = os.getenv("ASTER_FUNDING_PROVIDER", "").strip()
    if not value:
        raise HTTPException(503, "Funding provider is not configured")
    return value

def verify_signature(raw: bytes, signature: Optional[str]):
    secret = os.getenv("ASTER_FUNDING_WEBHOOK_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(503, "Funding webhook secret is not configured")
    if not signature:
        raise HTTPException(401, "Missing provider signature")
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid provider signature")

@router.post("/v1/wallet/deposits", status_code=201)
def create_deposit(body: DepositCreateIn, user: User = Depends(current_user), dbs: Session = Depends(db),
                   _: None = Depends(require_csrf), idem: str = Depends(require_idempotency_key)):
    provider = provider_name()
    existing = dbs.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id == user.id,
        IdempotencyKey.key == idem, IdempotencyKey.endpoint == "/v1/wallet/deposits"))
    if existing:
        return json.loads(existing.response_body)
    intent = DepositIntent(user_id=user.id, provider=provider, currency=body.currency,
                           network=body.network, status="pending")
    dbs.add(intent)
    dbs.flush()
    result = {"id": intent.id, "status": intent.status, "provider": provider,
              "currency": intent.currency, "network": intent.network,
              "deposit_address": intent.deposit_address,
              "provider_reference": intent.provider_reference}
    dbs.add(IdempotencyKey(user_id=user.id, key=idem, endpoint="/v1/wallet/deposits",
                           response_status=201, response_body=json.dumps(result)))
    dbs.commit()
    return result

@router.post("/v1/wallet/provider/webhook")
async def funding_webhook(request: Request, dbs: Session = Depends(db)):
    raw = await request.body()
    verify_signature(raw, request.headers.get("X-Aster-Provider-Signature"))
    try:
        body = ProviderWebhookIn.model_validate_json(raw)
    except Exception:
        raise HTTPException(400, "Invalid provider payload")
    provider = provider_name()
    existing = dbs.scalar(select(ProviderEvent).where(ProviderEvent.event_id == body.event_id))
    if existing:
        return {"ok": True, "status": existing.status, "duplicate": True}
    intent = dbs.scalar(select(DepositIntent).where(DepositIntent.provider_reference == body.provider_reference))
    if not intent:
        raise HTTPException(404, "Deposit intent not found")
    if intent.provider != provider or intent.currency != body.currency or intent.network != body.network:
        raise HTTPException(409, "Provider or asset mismatch")
    event = ProviderEvent(provider=provider, event_id=body.event_id, event_type=body.event_type,
                          payload_hash=hashlib.sha256(raw).hexdigest())
    dbs.add(event)
    if body.status == "confirmed":
        if intent.status != "confirmed":
            if intent.amount is not None and intent.amount != body.amount:
                raise HTTPException(409, "Deposit amount mismatch")
            w = dbs.scalar(select(Wallet).where(Wallet.user_id == intent.user_id).with_for_update())
            if not w:
                raise HTTPException(404, "Wallet not found")
            ref = "DEP-" + body.event_id
            post_double_entry(dbs, user_id=intent.user_id, reference=ref, amount=body.amount,
                              debit_account="user.available", credit_account="platform.funding")
            w.available += body.amount
            dbs.add(LedgerEntry(user_id=intent.user_id, kind="deposit", amount=body.amount,
                                reference=ref, currency=intent.currency, status="posted"))
            intent.amount = body.amount
            intent.status = "confirmed"
    elif body.status == "failed":
        intent.status = "failed"
    else:
        if intent.status == "confirmed":
            raise HTTPException(409, "Confirmed deposit cannot be reversed without a compensating settlement")
        intent.status = "reversed"
    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    dbs.commit()
    return {"ok": True, "status": intent.status, "deposit_id": intent.id}

@router.post("/v1/wallet/withdrawals", status_code=201)
def create_withdrawal(body: WithdrawalCreateIn, user: User = Depends(current_user), dbs: Session = Depends(db),
                      _: None = Depends(require_csrf), idem: str = Depends(require_idempotency_key)):
    provider = provider_name()
    existing = dbs.scalar(select(IdempotencyKey).where(IdempotencyKey.user_id == user.id,
        IdempotencyKey.key == idem, IdempotencyKey.endpoint == "/v1/wallet/withdrawals"))
    if existing:
        return json.loads(existing.response_body)
    ref = "WD-" + secrets.token_hex(6).upper()
    transfer_wallet_balance(dbs, user_id=user.id, amount=body.amount,
                            source="user.available", destination="user.pending", reference=ref)
    w = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id).with_for_update())
    w.available -= body.amount
    w.pending += body.amount
    request = WithdrawalRequest(user_id=user.id, provider=provider, currency=body.currency,
                                network=body.network, address=body.address, amount=body.amount)
    dbs.add(request)
    dbs.flush()
    dbs.add(LedgerEntry(user_id=user.id, kind="withdrawal", amount=-body.amount,
                        reference=ref, currency=body.currency, status="pending"))
    result = {"id": request.id, "status": request.status, "provider": provider,
              "amount": str(request.amount), "currency": request.currency,
              "network": request.network, "address": request.address,
              "provider_reference": request.provider_reference}
    dbs.add(IdempotencyKey(user_id=user.id, key=idem, endpoint="/v1/wallet/withdrawals",
                           response_status=201, response_body=json.dumps(result)))
    dbs.commit()
    return result

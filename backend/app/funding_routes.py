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
from app.main import (
    User,
    Wallet,
    LedgerEntry,
    IdempotencyKey,
    current_user,
    db,
    require_csrf,
    require_idempotency_key,
    transfer_wallet_balance,
    post_double_entry,
    Referral,
    AuditEvent,
)
from app.treasury import NETWORKS, normalize_network, treasury_address, valid_address

router = APIRouter()

class DepositCreateIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)

class WithdrawalCreateIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)
    address: str = Field(min_length=10, max_length=256)
    amount: Decimal = Field(gt=0)



class WithdrawalWebhookIn(BaseModel):
    event_id: str = Field(min_length=8, max_length=200)
    event_type: str = Field(min_length=3, max_length=80)
    provider_reference: str = Field(min_length=3, max_length=160)
    status: str = Field(pattern="^(confirmed|failed|reversed)$")
    tx_hash: Optional[str] = Field(default=None, max_length=256)

class ProviderWebhookIn(BaseModel):
    event_id: str = Field(min_length=8, max_length=200)
    event_type: str = Field(min_length=3, max_length=80)
    provider_reference: str = Field(min_length=3, max_length=160)
    status: str = Field(pattern="^(confirmed|failed|reversed)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)

def provider_name():
    # Aster's first custody rail is its own treasury wallet. An external
    # processor can still be selected later by setting ASTER_FUNDING_PROVIDER.
    return os.getenv("ASTER_FUNDING_PROVIDER", "aster-treasury").strip() or "aster-treasury"

def verify_signature(raw: bytes, signature: Optional[str]):
    secret = os.getenv("ASTER_FUNDING_WEBHOOK_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(503, "Funding webhook secret is not configured")
    if not signature:
        raise HTTPException(401, "Missing provider signature")
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "Invalid provider signature")

@router.get("/v1/wallet/deposit-addresses")
def deposit_addresses():
    return {
        "currency": "USDT",
        "networks": [
            {
                "network": network,
                "name": meta["name"],
                "label": meta["label"],
                "address": treasury_address(network),
                "chain_id": meta["chain_id"],
                "decimals": meta["decimals"],
            }
            for network, meta in NETWORKS.items()
        ],
        "custody": "Aster treasury",
    }

@router.post("/v1/wallet/deposits", status_code=201)
def create_deposit(
    body: DepositCreateIn,
    user: User = Depends(current_user),
    dbs: Session = Depends(db),
    _: None = Depends(require_csrf),
    idem: str = Depends(require_idempotency_key),
):
    provider = provider_name()
    network = normalize_network(body.network)
    if network not in NETWORKS:
        raise HTTPException(422, "Unsupported USDT network. Use BEP20 or TRC20.")
    address = treasury_address(network)

    existing = dbs.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user.id,
            IdempotencyKey.key == idem,
            IdempotencyKey.endpoint == "/v1/wallet/deposits",
        )
    )
    if existing:
        return json.loads(existing.response_body)

    provider_reference = "AST-DEP-" + secrets.token_hex(10).upper()
    intent = DepositIntent(
        user_id=user.id,
        provider=provider,
        provider_reference=provider_reference,
        currency=body.currency,
        network=network,
        status="pending",
        deposit_address=address,
    )
    dbs.add(intent)
    dbs.flush()

    result = {
        "id": intent.id,
        "status": intent.status,
        "provider": provider,
        "custody": "Aster treasury",
        "currency": intent.currency,
        "network": intent.network,
        "network_name": NETWORKS[network]["name"],
        "deposit_address": intent.deposit_address,
        "provider_reference": intent.provider_reference,
        "credit_rule": "Credit only after the blockchain transfer is independently verified.",
    }
    dbs.add(
        IdempotencyKey(
            user_id=user.id,
            key=idem,
            endpoint="/v1/wallet/deposits",
            response_status=201,
            response_body=json.dumps(result),
        )
    )
    dbs.commit()
    return result

@router.get("/v1/wallet/deposits/{deposit_id}")
def get_deposit(
    deposit_id: int,
    user: User = Depends(current_user),
    dbs: Session = Depends(db),
):
    intent = dbs.scalar(
        select(DepositIntent).where(
            DepositIntent.id == deposit_id,
            DepositIntent.user_id == user.id,
        )
    )
    if not intent:
        raise HTTPException(404, "Deposit not found")
    return {
        "id": intent.id,
        "status": intent.status,
        "currency": intent.currency,
        "network": intent.network,
        "deposit_address": intent.deposit_address,
        "provider_reference": intent.provider_reference,
        "amount": str(intent.amount) if intent.amount is not None else None,
        "created_at": intent.created_at.isoformat(),
        "updated_at": intent.updated_at.isoformat(),
    }

@router.post("/v1/wallet/provider/webhook")
async def funding_webhook(request: Request, dbs: Session = Depends(db)):
    raw = await request.body()
    verify_signature(raw, request.headers.get("X-Aster-Provider-Signature"))
    try:
        body = ProviderWebhookIn.model_validate_json(raw)
    except Exception:
        raise HTTPException(400, "Invalid provider payload")

    provider = provider_name()
    network = normalize_network(body.network)
    if network not in NETWORKS:
        raise HTTPException(422, "Unsupported USDT network")

    existing = dbs.scalar(
        select(ProviderEvent).where(ProviderEvent.event_id == body.event_id)
    )
    if existing:
        return {"ok": True, "status": existing.status, "duplicate": True}

    intent = dbs.scalar(
        select(DepositIntent).where(
            DepositIntent.provider_reference == body.provider_reference
        )
    )
    if not intent:
        raise HTTPException(404, "Deposit intent not found")
    if (
        intent.provider != provider
        or intent.currency != body.currency
        or intent.network != network
    ):
        raise HTTPException(409, "Provider or asset mismatch")

    event = ProviderEvent(
        provider=provider,
        event_id=body.event_id,
        event_type=body.event_type,
        payload_hash=hashlib.sha256(raw).hexdigest(),
    )
    dbs.add(event)

    if body.status == "confirmed":
        if intent.status != "confirmed":
            if intent.amount is not None and intent.amount != body.amount:
                raise HTTPException(409, "Deposit amount mismatch")
            w = dbs.scalar(
                select(Wallet)
                .where(Wallet.user_id == intent.user_id)
                .with_for_update()
            )
            if not w:
                raise HTTPException(404, "Wallet not found")
            ref = "DEP-" + body.event_id
            post_double_entry(
                dbs,
                user_id=intent.user_id,
                reference=ref,
                amount=body.amount,
                debit_account="user.available",
                credit_account="platform.funding",
            )
            w.available += body.amount
            dbs.add(
                LedgerEntry(
                    user_id=intent.user_id,
                    kind="deposit",
                    amount=body.amount,
                    reference=ref,
                    currency=intent.currency,
                    status="posted",
                )
            )
            intent.amount = body.amount
            intent.status = "confirmed"
    elif body.status == "failed":
        intent.status = "failed"
    else:
        if intent.status == "confirmed":
            raise HTTPException(
                409,
                "Confirmed deposit cannot be reversed without a compensating settlement",
            )
        intent.status = "reversed"

    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    dbs.commit()
    return {"ok": True, "status": intent.status, "deposit_id": intent.id}

@router.post("/v1/wallet/withdrawals", status_code=201)
def create_withdrawal(
    body: WithdrawalCreateIn,
    user: User = Depends(current_user),
    dbs: Session = Depends(db),
    _: None = Depends(require_csrf),
    idem: str = Depends(require_idempotency_key),
):
    provider = provider_name()
    network = normalize_network(body.network)
    if network not in NETWORKS:
        raise HTTPException(422, "Unsupported USDT network. Use BEP20 or TRC20.")
    if not valid_address(network, body.address):
        raise HTTPException(422, "Invalid destination address for the selected network.")

    existing = dbs.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user.id,
            IdempotencyKey.key == idem,
            IdempotencyKey.endpoint == "/v1/wallet/withdrawals",
        )
    )
    if existing:
        return json.loads(existing.response_body)

    ref = "WD-" + secrets.token_hex(6).upper()
    transfer_wallet_balance(
        dbs,
        user_id=user.id,
        amount=body.amount,
        source="user.available",
        destination="user.pending",
        reference=ref,
    )
    w = dbs.scalar(
        select(Wallet).where(Wallet.user_id == user.id).with_for_update()
    )
    w.available -= body.amount
    w.pending += body.amount

    request = WithdrawalRequest(
        user_id=user.id,
        provider=provider,
        currency=body.currency,
        network=network,
        address=body.address,
        amount=body.amount,
    )
    dbs.add(request)
    dbs.flush()
    dbs.add(
        LedgerEntry(
            user_id=user.id,
            kind="withdrawal",
            amount=-body.amount,
            reference=ref,
            currency=body.currency,
            status="pending",
        )
    )

    result = {
        "id": request.id,
        "status": request.status,
        "provider": provider,
        "custody": "Aster treasury",
        "amount": str(request.amount),
        "currency": request.currency,
        "network": request.network,
        "address": request.address,
        "provider_reference": request.provider_reference,
    }
    dbs.add(
        IdempotencyKey(
            user_id=user.id,
            key=idem,
            endpoint="/v1/wallet/withdrawals",
            response_status=201,
            response_body=json.dumps(result),
        )
    )
    dbs.commit()
    return result


@router.get("/v1/wallet/withdrawals")
def list_withdrawals(user: User = Depends(current_user), dbs: Session = Depends(db)):
    rows = dbs.scalars(select(WithdrawalRequest).where(WithdrawalRequest.user_id == user.id).order_by(WithdrawalRequest.id.desc()).limit(100)).all()
    return [{"id":r.id,"status":r.status,"amount":str(r.amount),"currency":r.currency,"network":r.network,"address":r.address,"provider_reference":r.provider_reference,"created_at":r.created_at.isoformat(),"updated_at":r.updated_at.isoformat()} for r in rows]

@router.get("/v1/wallet/withdrawals/{withdrawal_id}")
def get_withdrawal(withdrawal_id:int,user:User=Depends(current_user),dbs:Session=Depends(db)):
    r=dbs.scalar(select(WithdrawalRequest).where(WithdrawalRequest.id==withdrawal_id,WithdrawalRequest.user_id==user.id))
    if not r: raise HTTPException(404,"Withdrawal not found")
    return {"id":r.id,"status":r.status,"amount":str(r.amount),"currency":r.currency,"network":r.network,"address":r.address,"provider_reference":r.provider_reference,"created_at":r.created_at.isoformat(),"updated_at":r.updated_at.isoformat()}

@router.post("/v1/wallet/withdrawals/webhook")
async def withdrawal_webhook(request: Request, dbs: Session = Depends(db)):
    raw=await request.body(); verify_signature(raw, request.headers.get("X-Aster-Provider-Signature"))
    try: body=WithdrawalWebhookIn.model_validate_json(raw)
    except Exception: raise HTTPException(400,"Invalid withdrawal provider payload")
    provider=provider_name()
    existing=dbs.scalar(select(ProviderEvent).where(ProviderEvent.event_id==body.event_id))
    if existing: return {"ok":True,"status":existing.status,"duplicate":True}
    row=dbs.scalar(select(WithdrawalRequest).where(WithdrawalRequest.provider_reference==body.provider_reference))
    if not row or row.provider != provider: raise HTTPException(404,"Withdrawal request not found")
    event=ProviderEvent(provider=provider,event_id=body.event_id,event_type=body.event_type,payload_hash=hashlib.sha256(raw).hexdigest()); dbs.add(event)
    if row.status == "confirmed":
        event.status="processed"; event.processed_at=datetime.now(timezone.utc); dbs.commit(); return {"ok":True,"status":"confirmed","duplicate":True}
    w=dbs.scalar(select(Wallet).where(Wallet.user_id==row.user_id).with_for_update())
    if not w: raise HTTPException(404,"Wallet not found")
    ref="WD-"+str(row.id)
    if body.status == "confirmed":
        post_double_entry(dbs,user_id=row.user_id,reference=ref+"-SETTLED",amount=row.amount,debit_account="platform.withdrawals",credit_account="user.pending")
        w.pending -= row.amount
        row.status="confirmed"
        entry=dbs.scalar(select(LedgerEntry).where(LedgerEntry.reference==ref))
        if entry: entry.status="posted"
        dbs.add(AuditEvent(user_id=row.user_id,event_type="withdrawal_confirmed",metadata_json=json.dumps({"withdrawal_id":row.id,"tx_hash":body.tx_hash})))
    else:
        post_double_entry(dbs,user_id=row.user_id,reference=ref+"-RELEASE",amount=row.amount,debit_account="user.available",credit_account="user.pending")
        w.pending -= row.amount; w.available += row.amount; row.status=body.status
        entry=dbs.scalar(select(LedgerEntry).where(LedgerEntry.reference==ref))
        if entry: entry.status="reversed"
        dbs.add(LedgerEntry(user_id=row.user_id,kind="withdrawal_reversal",amount=row.amount,reference=ref+"-RELEASE",currency=row.currency,status="posted"))
        dbs.add(AuditEvent(user_id=row.user_id,event_type="withdrawal_released",metadata_json=json.dumps({"withdrawal_id":row.id,"reason":body.status})))
    event.status="processed"; event.processed_at=datetime.now(timezone.utc); dbs.commit()
    return {"ok":True,"status":row.status,"withdrawal_id":row.id,"tx_hash":body.tx_hash}

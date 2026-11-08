import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
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
    accrue_referral_commissions,
)
from app.treasury import NETWORKS, normalize_network, treasury_address, valid_address
from app.withdrawal_engine import reconcile_withdrawal_confirmation, reconcile_withdrawal_failure

router = APIRouter()

class DepositCreateIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)
    expected_amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=28, decimal_places=6)

class WithdrawalCreateIn(BaseModel):
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)
    address: str = Field(min_length=10, max_length=256)
    amount: Decimal = Field(gt=0, max_digits=28, decimal_places=8)


class WithdrawalWebhookIn(BaseModel):
    event_id: str = Field(min_length=8, max_length=200)
    event_type: str = Field(min_length=3, max_length=80)
    provider_reference: str = Field(min_length=3, max_length=160)
    status: str = Field(pattern="^(confirmed|failed)$")
    tx_hash: Optional[str] = Field(default=None, max_length=256)

class ProviderWebhookIn(BaseModel):
    event_id: str = Field(min_length=8, max_length=200)
    event_type: str = Field(min_length=3, max_length=80)
    provider_reference: str = Field(min_length=3, max_length=160)
    status: str = Field(pattern="^(confirmed|failed|reversed)$")
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USDT", pattern="^USDT$")
    network: str = Field(min_length=2, max_length=32)

def require_verified_kyc(user: User) -> None:
    if user.kyc_status != "verified":
        raise HTTPException(403, "Identity verification must be completed before deposits or withdrawals.")


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


def expire_unsubmitted_deposit_tickets(dbs: Session) -> int:
    """Release expired tickets only when no TXID was submitted."""
    now = datetime.now(timezone.utc)
    rows = dbs.scalars(select(DepositIntent).where(
        DepositIntent.ticket_mode == "single_wallet_ticket_v1",
        DepositIntent.status == "pending",
        DepositIntent.tx_hash.is_(None),
        DepositIntent.expires_at.is_not(None),
        DepositIntent.expires_at < now,
    )).all()
    for row in rows:
        row.status = "expired"
        row.updated_at = now
        dbs.add(AuditEvent(
            user_id=row.user_id,
            event_type="deposit_ticket_expired",
            metadata_json=json.dumps({"deposit_id": row.id, "ticket_id": row.provider_reference, "network": row.network}),
        ))
    if rows:
        dbs.flush()
    return len(rows)


def reserve_deposit_ticket_amount(dbs: Session, network: str, requested: Decimal) -> Decimal:
    """Reserve a unique six-decimal amount for active tickets on this network.

    The unique partial database index is the final concurrency guard. The
    returned amount is a routing hint, not proof of customer identity.
    """
    quantum = Decimal("0.000001")
    base = requested.quantize(quantum, rounding=ROUND_DOWN)
    if base != requested:
        raise HTTPException(422, "USDT deposit amounts support up to 6 decimal places on both networks.")
    active = dbs.scalars(select(DepositIntent.amount).where(
        DepositIntent.network == network,
        DepositIntent.status.in_(["pending", "transaction_submitted", "review_required"]),
    )).all()
    reserved = {Decimal(value) for value in active if value is not None}
    for offset in range(100000):
        candidate = base + (quantum * offset)
        if candidate not in reserved:
            return candidate
    raise HTTPException(503, "Unable to reserve a unique deposit amount. Please try again later.")

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
    require_verified_kyc(user)
    if body.expected_amount is None:
        raise HTTPException(422, "Enter the amount you intend to deposit so Aster can reserve a unique ticket amount.")
    expire_unsubmitted_deposit_tickets(dbs)

    requested_amount = body.expected_amount
    reserved_amount = reserve_deposit_ticket_amount(dbs, network, requested_amount)
    ttl_minutes = max(30, min(60, int(os.getenv("ASTER_DEPOSIT_TICKET_TTL_MINUTES", "45"))))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    provider_reference = "AST-DEP-" + secrets.token_hex(10).upper()
    intent = DepositIntent(
        user_id=user.id,
        provider=provider,
        provider_reference=provider_reference,
        currency=body.currency,
        network=network,
        status="pending",
        deposit_address=address,
        amount=reserved_amount,
        requested_amount=requested_amount,
        expires_at=expires_at,
        ticket_mode="single_wallet_ticket_v1",
    )
    dbs.add(intent)
    try:
        dbs.flush()
    except IntegrityError:
        dbs.rollback()
        raise HTTPException(409, "A concurrent deposit ticket reserved that amount. Please create a new ticket.")

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
        "ticket_id": intent.provider_reference,
        "requested_amount": str(intent.requested_amount),
        "expected_amount": str(intent.amount) if intent.amount is not None else None,
        "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
        "ticket_ttl_minutes": ttl_minutes,
        "credit_rule": "Submit the TXID before expiry. Aster independently verifies the chain transfer; shared-wallet ownership matches remain subject to review before credit.",
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
    try:
        dbs.commit()
    except IntegrityError:
        dbs.rollback()
        raise HTTPException(409, "A concurrent deposit ticket reserved that amount. Please create a new ticket.")
    return result

@router.post("/v1/wallet/deposits/{deposit_id}/transaction")
def submit_deposit_transaction(
    deposit_id: int,
    body: dict,
    user: User = Depends(current_user),
    dbs: Session = Depends(db),
    _: None = Depends(require_csrf),
):
    raw_hash = str(body.get("tx_hash", "")).strip()
    network_hint = dbs.scalar(select(DepositIntent).where(
        DepositIntent.id == deposit_id, DepositIntent.user_id == user.id
    ))
    if not network_hint:
        raise HTTPException(404, "Deposit not found")
    if network_hint.status == "pending" and network_hint.expires_at:
        expiry = network_hint.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expiry:
            network_hint.status = "expired"
            dbs.commit()
            raise HTTPException(410, "This deposit ticket has expired. Create a new ticket before sending funds.")
    if network_hint.status not in {"pending", "transaction_submitted", "review_required"}:
        raise HTTPException(409, "This deposit ticket is no longer active")
    if network_hint.tx_hash:
        if network_hint.tx_hash == raw_hash:
            return {"id": network_hint.id, "status": network_hint.status, "tx_hash": raw_hash,
                    "message": "This transaction ID is already attached to your deposit ticket."}
        raise HTTPException(409, "A transaction hash is already attached to this deposit")
    if network_hint.network == "BEP20":
        if not re.fullmatch(r"0x[a-fA-F0-9]{64}", raw_hash):
            raise HTTPException(422, "Enter a valid BNB Smart Chain transaction hash")
        normalized_hash = raw_hash.lower()
    else:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", raw_hash):
            raise HTTPException(422, "Enter a valid TRON transaction hash")
        normalized_hash = raw_hash.lower()
    duplicate = dbs.scalar(select(DepositIntent).where(DepositIntent.tx_hash == normalized_hash))
    if duplicate:
        raise HTTPException(409, "This transaction hash is already linked to a deposit")
    network_hint.tx_hash = normalized_hash
    network_hint.status = "transaction_submitted"
    network_hint.updated_at = datetime.now(timezone.utc)

    # Reconcile a transfer the chain worker may have observed before the user submitted its hash.
    from app.blockchain import credit_transfer
    from app.funding import BlockchainTransfer
    # Both chains can emit multiple token-transfer events in one transaction.
    # Reconcile only when the submitted transaction resolves to exactly one
    # treasury transfer; otherwise leave every event quarantined for review.
    observed = dbs.scalars(select(BlockchainTransfer).where(
        BlockchainTransfer.network == network_hint.network,
        or_(
            BlockchainTransfer.tx_hash.like(normalized_hash + ":%"),
            BlockchainTransfer.tx_hash == normalized_hash,  # legacy single-event rows
        ),
    )).all()
    if len(observed) == 1 and observed[0].status in {"quarantined", "confirmed", "review_required"}:
        observed[0].status = "confirmed"
        credit_transfer(dbs, observed[0])

    dbs.add(AuditEvent(
        user_id=user.id,
        event_type="deposit_transaction_submitted",
        metadata_json=json.dumps({"deposit_id": deposit_id, "network": network_hint.network, "tx_hash": normalized_hash}),
    ))
    dbs.commit()
    return {"id": network_hint.id, "status": network_hint.status, "tx_hash": normalized_hash,
            "message": "Transaction submitted. Aster will verify the on-chain transfer and match its ticket amount. Funds remain uncredited until member ownership is independently confirmed through attribution review."}

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
        "tx_hash": intent.tx_hash,
        "amount": str(intent.amount) if intent.amount is not None else None,
        "expected_amount": str(intent.amount) if intent.amount is not None else None,
        "requested_amount": str(intent.requested_amount) if intent.requested_amount is not None else None,
        "ticket_id": intent.provider_reference,
        "expires_at": intent.expires_at.isoformat() if intent.expires_at else None,
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

    payload_hash = hashlib.sha256(raw).hexdigest()
    existing = dbs.scalar(
        select(ProviderEvent).where(ProviderEvent.event_id == body.event_id)
    )
    if existing:
        if existing.provider != provider or existing.payload_hash != payload_hash:
            raise HTTPException(409, "Provider event ID was reused with a different payload")
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
        payload_hash=payload_hash,
    )
    dbs.add(event)

    if body.status == "confirmed":
        owner = dbs.scalar(select(User).where(User.id == intent.user_id))
        if not owner or owner.kyc_status != "verified":
            raise HTTPException(409, "Deposit cannot be credited until identity verification is complete")
        if intent.status not in {"pending", "confirmed"}:
            raise HTTPException(409, f"Deposit intent cannot be confirmed from {intent.status}")
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
            accrue_referral_commissions(
                dbs,
                depositing_user_id=intent.user_id,
                deposit_amount=body.amount,
                source_reference=ref,
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
    if network != "BEP20":
        raise HTTPException(422, "Withdrawals are currently available only on BNB Smart Chain (USDT-BEP20).")
    if not valid_address(network, body.address):
        raise HTTPException(422, "Invalid BEP20 destination address. Use a valid 0x address.")

    existing = dbs.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user.id,
            IdempotencyKey.key == idem,
            IdempotencyKey.endpoint == "/v1/wallet/withdrawals",
        )
    )
    if existing:
        return json.loads(existing.response_body)
    require_verified_kyc(user)

    provider_reference = "AST-WD-" + secrets.token_hex(10).upper()
    ref = "WD-" + provider_reference
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
        provider_reference=provider_reference,
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
    raw = await request.body()
    verify_signature(raw, request.headers.get("X-Aster-Provider-Signature"))
    try:
        body = WithdrawalWebhookIn.model_validate_json(raw)
    except Exception:
        raise HTTPException(400, "Invalid withdrawal provider payload")

    provider = provider_name()
    payload_hash = hashlib.sha256(raw).hexdigest()
    existing = dbs.scalar(
        select(ProviderEvent).where(ProviderEvent.event_id == body.event_id)
    )
    if existing:
        if existing.provider != provider or existing.payload_hash != payload_hash:
            raise HTTPException(409, "Provider event ID was reused with a different payload")
        row = dbs.scalar(
            select(WithdrawalRequest).where(
                WithdrawalRequest.provider_reference == body.provider_reference
            )
        )
        if row and row.status in {"confirmed", "failed", "reversed"}:
            if existing.status != "processed":
                existing.status = "processed"
                existing.processed_at = datetime.now(timezone.utc)
                dbs.commit()
            return {"ok": True, "status": row.status, "duplicate": True}
        return {"ok": True, "status": existing.status, "duplicate": True}

    row = dbs.scalar(
        select(WithdrawalRequest).where(
            WithdrawalRequest.provider_reference == body.provider_reference
        )
    )
    if not row or row.provider != provider:
        raise HTTPException(404, "Withdrawal request not found")
    if body.status == "confirmed" and row.network != "BEP20":
        raise HTTPException(409, "Only USDT-BEP20 withdrawals can be confirmed for processing.")

    event = ProviderEvent(
        provider=provider,
        event_id=body.event_id,
        event_type=body.event_type,
        payload_hash=payload_hash,
    )
    dbs.add(event)

    try:
        if body.status == "confirmed":
            result = reconcile_withdrawal_confirmation(
                dbs,
                provider_reference=body.provider_reference,
                tx_hash=body.tx_hash,
            )
        else:
            result = reconcile_withdrawal_failure(
                dbs,
                provider_reference=body.provider_reference,
                reason=body.status,
            )
    except ValueError as exc:
        dbs.rollback()
        raise HTTPException(409, str(exc))

    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    dbs.commit()
    return {
        "ok": True,
        "status": result["status"],
        "withdrawal_id": row.id,
        "tx_hash": body.tx_hash,
        "duplicate": bool(result.get("duplicate", False)),
    }

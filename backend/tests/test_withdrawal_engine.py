from decimal import Decimal

from app.funding import WithdrawalRequest
from app.main import LedgerEntry, SessionLocal, User, Wallet
from app.withdrawal_engine import (
    DryRunWithdrawalProvider,
    process_pending_withdrawals,
    reconcile_withdrawal_confirmation,
)


def test_withdrawal_engine_submits_then_reconciles_idempotently():
    db = SessionLocal()
    email = "engine-" + __import__("secrets").token_hex(5) + "@example.com"
    user = User(
        email=email,
        password_hash="test",
        status="active",
        referral_code="ENGINE-" + __import__("secrets").token_hex(4).upper(),
    )
    db.add(user)
    db.flush()
    wallet = Wallet(user_id=user.id, available=Decimal("0"), invested=Decimal("0"), pending=Decimal("5"))
    db.add(wallet)
    row = WithdrawalRequest(
        user_id=user.id,
        provider="aster-treasury",
        provider_reference="AST-WD-ENGINE-" + __import__("secrets").token_hex(4).upper(),
        currency="USDT",
        network="TRC20",
        address="T" + "1" * 33,
        amount=Decimal("5"),
        status="pending",
    )
    db.add(row)
    db.flush()
    db.add(
        LedgerEntry(
            user_id=user.id,
            kind="withdrawal",
            amount=Decimal("-5"),
            reference="WD-" + row.provider_reference,
            currency="USDT",
            status="pending",
        )
    )
    db.commit()

    result = process_pending_withdrawals(db, DryRunWithdrawalProvider())
    assert result[0]["status"] == "submitted"
    assert result[0]["tx_hash"] == f"DRYRUN-{row.id}"

    settled = reconcile_withdrawal_confirmation(
        db,
        provider_reference=row.provider_reference,
        tx_hash=result[0]["tx_hash"],
    )
    assert settled["status"] == "confirmed"

    duplicate = reconcile_withdrawal_confirmation(
        db,
        provider_reference=row.provider_reference,
        tx_hash=result[0]["tx_hash"],
    )
    assert duplicate["duplicate"] is True

    db.refresh(wallet)
    db.refresh(row)
    assert row.status == "confirmed"
    assert wallet.pending == Decimal("0.00000000")
    db.close()

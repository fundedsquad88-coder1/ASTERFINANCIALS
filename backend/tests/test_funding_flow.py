import os
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import blockchain
from app.funding import DepositIntent, WithdrawalRequest
from app.main import Base, User, Wallet, LedgerEntry
from app.treasury import BEP20, treasury_address
from app.withdrawal_engine import (
    DryRunWithdrawalProvider,
    process_pending_withdrawals,
    reconcile_withdrawal_confirmation,
)


def test_deposit_to_withdrawal_dry_run_lifecycle():
    os.environ["ASTER_SKIP_CREATE_ALL"] = "true"
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()

    user = User(
        email="flow@example.com",
        password_hash="test",
        referral_code="FLOWREF",
        status="active",
        kyc_status="unverified",
    )
    db.add(user)
    db.flush()
    wallet = Wallet(user_id=user.id, available=Decimal("0"), invested=Decimal("0"), pending=Decimal("0"))
    db.add(wallet)
    intent = DepositIntent(
        user_id=user.id,
        provider="aster-treasury",
        provider_reference="AST-DEP-FLOW",
        currency="USDT",
        network=BEP20,
        amount=Decimal("25"),
        status="pending",
        deposit_address=treasury_address(BEP20),
    )
    db.add(intent)
    db.flush()

    transfer = blockchain.BlockchainTransfer(
        network=BEP20,
        tx_hash="0xflow:0",
        log_index=0,
        block_number=100,
        token_contract=blockchain.DEFAULT_BSC_USDT,
        from_address="0x" + "1" * 40,
        to_address=treasury_address(BEP20),
        amount=Decimal("25"),
        confirmations=12,
        status="confirmed",
    )
    db.add(transfer)
    db.flush()

    assert blockchain.credit_transfer(db, transfer) is True
    db.commit()
    db.refresh(wallet)
    assert wallet.available == Decimal("25.00000000")

    provider_reference = "AST-WD-FLOW"
    db.add(
        WithdrawalRequest(
            user_id=user.id,
            provider="aster-treasury",
            provider_reference=provider_reference,
            currency="USDT",
            network=BEP20,
            address="0x" + "2" * 40,
            amount=Decimal("10"),
            status="pending",
        )
    )
    db.add(
        LedgerEntry(
            user_id=user.id,
            kind="withdrawal",
            amount=Decimal("-10"),
            reference="WD-" + provider_reference,
            currency="USDT",
            status="pending",
        )
    )
    wallet.available -= Decimal("10")
    wallet.pending += Decimal("10")
    db.commit()

    submitted = process_pending_withdrawals(db, DryRunWithdrawalProvider(), limit=10)
    assert submitted[0]["status"] == "submitted"
    assert submitted[0]["provider_reference"] == provider_reference

    confirmed = reconcile_withdrawal_confirmation(
        db,
        provider_reference=provider_reference,
        tx_hash=submitted[0]["tx_hash"],
    )
    assert confirmed["status"] == "confirmed"

    db.refresh(wallet)
    assert wallet.available == Decimal("15.00000000")
    assert wallet.pending == Decimal("0.00000000")
    db.close()

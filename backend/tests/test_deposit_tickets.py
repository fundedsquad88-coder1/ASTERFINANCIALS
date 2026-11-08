import os
os.environ["ASTER_SKIP_CREATE_ALL"] = "true"

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import blockchain
from app.funding import BlockchainTransfer, DepositIntent
from app.funding_routes import expire_unsubmitted_deposit_tickets, reserve_deposit_ticket_amount
from app.main import Base, User, Wallet
from app.treasury import BEP20, TRC20, treasury_address


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def make_user(dbs):
    user = User(
        email="ticket-user@example.com",
        password_hash="test",
        referral_code="TICKETUSER",
        status="active",
        kyc_status="verified",
    )
    dbs.add(user)
    dbs.flush()
    dbs.add(Wallet(user_id=user.id, available=Decimal("0"), invested=Decimal("0"), pending=Decimal("0")))
    dbs.flush()
    return user


def test_ticket_amount_reservation_is_unique_per_network_and_active_ticket():
    dbs = make_session()
    user = make_user(dbs)
    dbs.add(DepositIntent(
        user_id=user.id,
        provider="aster-treasury",
        provider_reference="AST-DEP-ONE",
        currency="USDT",
        network=BEP20,
        amount=Decimal("100.000000"),
        requested_amount=Decimal("100.000000"),
        status="pending",
        deposit_address=treasury_address(BEP20),
        ticket_mode="single_wallet_ticket_v1",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    ))
    dbs.flush()

    assert reserve_deposit_ticket_amount(dbs, BEP20, Decimal("100")) == Decimal("100.000001")
    # The same amount may be reserved independently on a different chain.
    assert reserve_deposit_ticket_amount(dbs, TRC20, Decimal("100")) == Decimal("100.000000")
    dbs.close()


def test_expired_unsubmitted_ticket_releases_its_amount_reservation():
    dbs = make_session()
    user = make_user(dbs)
    expired = DepositIntent(
        user_id=user.id,
        provider="aster-treasury",
        provider_reference="AST-DEP-EXPIRED",
        currency="USDT",
        network=TRC20,
        amount=Decimal("25.000000"),
        requested_amount=Decimal("25.000000"),
        status="pending",
        deposit_address=treasury_address(TRC20),
        ticket_mode="single_wallet_ticket_v1",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    dbs.add(expired)
    dbs.flush()

    assert expire_unsubmitted_deposit_tickets(dbs) == 1
    dbs.commit()
    assert expired.status == "expired"
    assert reserve_deposit_ticket_amount(dbs, TRC20, Decimal("25")) == Decimal("25.000000")
    dbs.close()


def test_txid_and_exact_ticket_amount_create_review_candidate_not_automatic_credit():
    dbs = make_session()
    user = make_user(dbs)
    tx_hash = "0x" + "a" * 64
    intent = DepositIntent(
        user_id=user.id,
        provider="aster-treasury",
        provider_reference="AST-DEP-CANDIDATE",
        currency="USDT",
        network=BEP20,
        amount=Decimal("25.000001"),
        requested_amount=Decimal("25"),
        status="transaction_submitted",
        deposit_address=treasury_address(BEP20),
        tx_hash=tx_hash,
        ticket_mode="single_wallet_ticket_v1",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
    )
    dbs.add(intent)
    dbs.flush()

    transfer = BlockchainTransfer(
        network=BEP20,
        tx_hash=tx_hash + ":0",
        log_index=0,
        block_number=100,
        token_contract=blockchain.DEFAULT_BSC_USDT,
        from_address="0x" + "1" * 40,
        to_address=treasury_address(BEP20),
        amount=Decimal("25.000001"),
        confirmations=20,
        chain_timestamp=datetime.now(timezone.utc),
        status="confirmed",
    )
    dbs.add(transfer)
    dbs.flush()

    assert blockchain.credit_transfer(dbs, transfer) is False
    assert transfer.status == "review_required"
    assert transfer.deposit_intent_id == intent.id
    assert intent.status == "review_required"
    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet.available == Decimal("0")

    # The separately authenticated/admin-approved attribution path can post once.
    transfer.status = "confirmed"
    assert blockchain.credit_transfer(dbs, transfer, attribution_verified=True) is True
    dbs.commit()
    dbs.refresh(wallet)
    assert wallet.available == Decimal("25.000001")
    assert transfer.status == "credited"
    assert intent.status == "confirmed"
    dbs.close()


def test_wrong_usdt_contract_never_becomes_a_deposit_candidate():
    dbs = make_session()
    user = make_user(dbs)
    tx_hash = "0x" + "b" * 64
    intent = DepositIntent(
        user_id=user.id,
        provider="aster-treasury",
        provider_reference="AST-DEP-WRONG-CONTRACT",
        currency="USDT",
        network=BEP20,
        amount=Decimal("5.000000"),
        status="transaction_submitted",
        deposit_address=treasury_address(BEP20),
        tx_hash=tx_hash,
        ticket_mode="single_wallet_ticket_v1",
    )
    dbs.add(intent)
    dbs.flush()
    transfer = BlockchainTransfer(
        network=BEP20,
        tx_hash=tx_hash + ":0",
        log_index=0,
        block_number=100,
        token_contract="0x" + "f" * 40,
        from_address="0x" + "1" * 40,
        to_address=treasury_address(BEP20),
        amount=Decimal("5"),
        confirmations=20,
        status="confirmed",
    )
    dbs.add(transfer)
    dbs.flush()

    assert blockchain.credit_transfer(dbs, transfer) is False
    assert transfer.status == "quarantined"
    assert transfer.deposit_intent_id is None
    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet.available == Decimal("0")
    dbs.close()


def test_historical_transfer_cannot_be_claimed_by_a_new_ticket():
    dbs = make_session()
    user = make_user(dbs)
    now = datetime.now(timezone.utc)
    tx_hash = "0x" + "c" * 64
    intent = DepositIntent(
        user_id=user.id,
        provider="aster-treasury",
        provider_reference="AST-DEP-HISTORICAL",
        currency="USDT",
        network=BEP20,
        amount=Decimal("9.000001"),
        requested_amount=Decimal("9"),
        status="transaction_submitted",
        deposit_address=treasury_address(BEP20),
        tx_hash=tx_hash,
        ticket_mode="single_wallet_ticket_v1",
        created_at=now,
        expires_at=now + timedelta(minutes=45),
    )
    dbs.add(intent)
    dbs.flush()
    transfer = BlockchainTransfer(
        network=BEP20,
        tx_hash=tx_hash + ":0",
        log_index=0,
        block_number=99,
        token_contract=blockchain.DEFAULT_BSC_USDT,
        from_address="0x" + "2" * 40,
        to_address=treasury_address(BEP20),
        amount=Decimal("9.000001"),
        confirmations=20,
        chain_timestamp=now - timedelta(days=1),
        status="confirmed",
    )
    dbs.add(transfer)
    dbs.flush()

    assert blockchain.credit_transfer(dbs, transfer) is False
    assert transfer.status == "review_required"
    assert transfer.deposit_intent_id == intent.id
    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet.available == Decimal("0")
    dbs.close()

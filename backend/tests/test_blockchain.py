import os
os.environ["ASTER_SKIP_CREATE_ALL"] = "true"

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import blockchain
from app.funding import BlockchainCursor, BlockchainTransfer, DepositIntent
from app.main import AuditEvent, Base, LedgerEntry, Referral, User, Wallet, accrue_referral_commissions
from app.treasury import BEP20, TRC20, treasury_address


def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def seed_user(dbs, amount=Decimal("0")):
    user = User(
        email="test@example.com",
        password_hash="test",
        referral_code="TESTREF",
        status="active",
        kyc_status="unverified",
    )
    dbs.add(user)
    dbs.flush()
    dbs.add(Wallet(user_id=user.id, available=amount, invested=0, pending=0))
    dbs.flush()
    return user


def test_treasury_addresses_are_valid_and_expected():
    assert treasury_address(BEP20) == "0xd7F76be1a1c4aC25dAf2DDAbFd51E15AB736012c"
    assert treasury_address(TRC20) == "TLkgCEs6zFk49FuEhMPzMbPfNjZ5UEGV3b"


def test_credit_transfer_requires_exactly_one_matching_intent():
    dbs = session()
    user = seed_user(dbs)
    intent = DepositIntent(
        user_id=user.id,
        provider="aster",
        currency="USDT",
        network=BEP20,
        amount=Decimal("100.00000000"),
        status="pending",
        deposit_address=treasury_address(BEP20),
        tx_hash="0x" + "e" * 64,
    )
    dbs.add(intent)
    dbs.flush()

    transfer = BlockchainTransfer(
        network=BEP20,
        tx_hash="0x" + "e" * 64,
        log_index=0,
        block_number=100,
        token_contract=blockchain.DEFAULT_BSC_USDT,
        from_address="0x" + "1" * 40,
        to_address=treasury_address(BEP20),
        amount=Decimal("100.00000000"),
        confirmations=12,
        status="confirmed",
    )
    dbs.add(transfer)
    dbs.flush()

    assert blockchain.credit_transfer(dbs, transfer) is True
    dbs.commit()

    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet.available == Decimal("100.00000000")
    assert transfer.status == "credited"
    assert transfer.deposit_intent_id == intent.id
    assert dbs.scalar(select(AuditEvent).where(AuditEvent.event_type == "blockchain_deposit_credited")) is not None


def test_credit_transfer_requires_exact_submitted_transaction_hash():
    dbs = session()
    user = seed_user(dbs)
    intent = DepositIntent(
        user_id=user.id, provider="aster", currency="USDT", network=BEP20,
        amount=None, status="pending", deposit_address=treasury_address(BEP20),
        tx_hash="0x" + "a" * 64,
    )
    dbs.add(intent)
    dbs.flush()
    transfer = BlockchainTransfer(
        network=BEP20, tx_hash="0x" + "b" * 64, log_index=0, block_number=10,
        token_contract=blockchain.DEFAULT_BSC_USDT, from_address="0x" + "1" * 40,
        to_address=treasury_address(BEP20), amount=Decimal("25"),
        confirmations=20, status="confirmed",
    )
    dbs.add(transfer)
    dbs.flush()
    assert blockchain.credit_transfer(dbs, transfer) is False
    assert transfer.status == "quarantined"
    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet.available == Decimal("0")
    dbs.close()


def test_credit_transfer_credits_exact_claimed_hash_once():
    dbs = session()
    user = seed_user(dbs)
    tx_hash = "0x" + "c" * 64
    intent = DepositIntent(
        user_id=user.id, provider="aster", currency="USDT", network=BEP20,
        amount=Decimal("25"), status="pending", deposit_address=treasury_address(BEP20),
        tx_hash=tx_hash,
    )
    dbs.add(intent)
    dbs.flush()
    transfer = BlockchainTransfer(
        network=BEP20, tx_hash=tx_hash, log_index=0, block_number=11,
        token_contract=blockchain.DEFAULT_BSC_USDT, from_address="0x" + "1" * 40,
        to_address=treasury_address(BEP20), amount=Decimal("25"),
        confirmations=20, status="confirmed",
    )
    dbs.add(transfer)
    dbs.flush()
    assert blockchain.credit_transfer(dbs, transfer) is True
    assert transfer.status == "credited"
    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))
    assert wallet.available == Decimal("25")
    assert blockchain.credit_transfer(dbs, transfer) is False
    dbs.close()


def test_credit_transfer_quarantines_ambiguous_match():
    dbs = session()
    user = seed_user(dbs)
    for _ in range(2):
        dbs.add(DepositIntent(
            user_id=user.id,
            provider="aster",
            currency="USDT",
            network=TRC20,
            amount=Decimal("50.00000000"),
            status="pending",
            deposit_address=treasury_address(TRC20),
        ))
    dbs.flush()

    transfer = BlockchainTransfer(
        network=TRC20,
        tx_hash="trx-ambiguous",
        block_number=1,
        token_contract=blockchain.DEFAULT_TRON_USDT,
        from_address="T" + "A" * 33,
        to_address=treasury_address(TRC20),
        amount=Decimal("50.00000000"),
        confirmations=1,
        status="confirmed",
    )
    dbs.add(transfer)
    dbs.flush()

    assert blockchain.credit_transfer(dbs, transfer) is False
    assert transfer.status == "quarantined"


def test_referral_rewards_accrue_pending_across_nine_levels_idempotently():
    dbs = session()
    users = []
    for index in range(4):
        user = User(
            email=f"level{index}@example.com",
            password_hash="test",
            referral_code=f"LEVEL{index}",
            status="active",
            kyc_status="verified",
        )
        dbs.add(user)
        dbs.flush()
        users.append(user)

    # users[0] refers users[1], who refers users[2], who refers users[3].
    for parent, child in zip(users[:-1], users[1:]):
        dbs.add(Referral(referrer_user_id=parent.id, referred_user_id=child.id))
    dbs.flush()

    first = accrue_referral_commissions(
        dbs,
        depositing_user_id=users[3].id,
        deposit_amount=Decimal("100"),
        source_reference="DEP-TEST-ONCE",
    )
    second = accrue_referral_commissions(
        dbs,
        depositing_user_id=users[3].id,
        deposit_amount=Decimal("100"),
        source_reference="DEP-TEST-ONCE",
    )
    dbs.commit()

    assert [item["amount"] for item in first] == ["10.00000000", "3.00000000", "2.00000000"]
    assert second == []
    links = dbs.scalars(select(Referral).order_by(Referral.id.asc())).all()
    assert [link.pending_bonus for link in links] == [
        Decimal("2.00000000"), Decimal("3.00000000"), Decimal("10.00000000")
    ]
    dbs.close()


def test_bsc_scan_deduplicates_transfer_and_advances_cursor(monkeypatch):
    dbs = session()
    user = seed_user(dbs)
    dbs.add(DepositIntent(
        user_id=user.id,
        provider="aster",
        currency="USDT",
        network=BEP20,
        amount=Decimal("12.50000000"),
        status="pending",
        deposit_address=treasury_address(BEP20),
        tx_hash="0xdeposit",
    ))
    dbs.flush()

    sender = "1" * 40
    recipient = treasury_address(BEP20)[2:].lower()
    amount_hex = hex(12_500000000000000000)
    log = {
        "transactionHash": "0xdeposit",
        "logIndex": "0x0",
        "blockNumber": "0x64",
        "topics": [blockchain.TRANSFER_TOPIC, "0x" + "0" * 24 + sender, "0x" + "0" * 24 + recipient],
        "data": amount_hex,
    }

    def fake_http(url, payload=None, headers=None):
        method = payload["method"]
        if method == "eth_blockNumber":
            return {"result": "0x70"}
        if method == "eth_getBlockByNumber":
            return {"result": {"number": "0x70"}}
        if method == "eth_getLogs":
            return {"result": [log]}
        raise AssertionError(method)

    monkeypatch.setattr(blockchain, "http_json", fake_http)
    monkeypatch.setenv("ASTER_BSC_RPC_URL", "http://test-rpc")
    monkeypatch.setenv("ASTER_BSC_START_BLOCK", "99")
    monkeypatch.setenv("ASTER_BSC_LOG_BATCH", "100")

    result = blockchain.bsc_scan(dbs)
    assert result["detected"] == 1
    assert result["credited"] == 1
    assert result["from_block"] == 100
    assert result["cursor"] == 112

    dbs.expire_all()
    assert dbs.scalar(select(BlockchainTransfer).where(BlockchainTransfer.tx_hash == "0xdeposit:0")) is not None
    assert dbs.scalar(select(BlockchainCursor).where(BlockchainCursor.network == BEP20)).cursor == 112



def test_tron_scan_follows_fingerprint_pages_without_skipping_timestamp(monkeypatch):
    dbs = session()
    user = seed_user(dbs)
    dbs.add(DepositIntent(
        user_id=user.id,
        provider="aster",
        currency="USDT",
        network=TRC20,
        amount=Decimal("5.000000"),
        status="pending",
        deposit_address=treasury_address(TRC20),
        tx_hash="trx-page-1",
    ))
    dbs.flush()

    def row(tx_hash):
        return {
            "transaction_id": tx_hash,
            "block_timestamp": 1700000000000,
            "token_info": {"address": blockchain.DEFAULT_TRON_USDT},
            "to": treasury_address(TRC20),
            "from": "T" + "A" * 33,
            "value": "5000000",
            "block": 123,
        }

    calls = []
    def fake_http(url, payload=None, headers=None):
        calls.append(url)
        if len(calls) == 1:
            return {"data": [row("trx-page-1")], "meta": {"fingerprint": "next-page-token"}}
        assert "fingerprint=next-page-token" in url
        return {"data": [row("trx-page-2")], "meta": {}}

    monkeypatch.setattr(blockchain, "http_json", fake_http)
    monkeypatch.setenv("ASTER_TRON_ENABLED", "true")
    monkeypatch.setenv("ASTER_TRON_API_URL", "https://tron.example")
    monkeypatch.setenv("ASTER_TRON_START_MS", "0")
    monkeypatch.setenv("ASTER_TRON_PAGE_SIZE", "1")

    result = blockchain.tron_scan(dbs)
    assert result["pages"] == 2
    assert result["detected"] == 2
    assert result["credited"] == 1
    assert result["has_more"] is False
    assert len(calls) == 2
    assert dbs.scalar(select(BlockchainCursor).where(BlockchainCursor.network == TRC20)).cursor == 1700000000000


def test_tron_scan_quarantines_multiple_treasury_events_in_one_transaction(monkeypatch):
    dbs = session()
    user = seed_user(dbs)
    tx_hash = "f" * 64
    dbs.add(DepositIntent(
        user_id=user.id,
        provider="aster",
        currency="USDT",
        network=TRC20,
        amount=Decimal("5.000000"),
        status="pending",
        deposit_address=treasury_address(TRC20),
        tx_hash=tx_hash,
    ))
    dbs.flush()

    def row(event_index, value):
        return {
            "transaction_id": tx_hash,
            "event_index": event_index,
            "block_timestamp": 1700000001000,
            "token_info": {"address": blockchain.DEFAULT_TRON_USDT},
            "to": treasury_address(TRC20),
            "from": "T" + "A" * 33,
            "value": str(value),
            "block": 124,
        }

    def fake_http(url, payload=None, headers=None):
        return {"data": [row(0, 5_000_000), row(1, 7_000_000)], "meta": {}}

    monkeypatch.setattr(blockchain, "http_json", fake_http)
    monkeypatch.setenv("ASTER_TRON_API_URL", "https://tron.example")
    monkeypatch.setenv("ASTER_TRON_START_MS", "0")
    monkeypatch.setenv("ASTER_TRON_PAGE_SIZE", "10")

    result = blockchain.tron_scan(dbs)
    transfers = dbs.scalars(
        select(BlockchainTransfer).where(BlockchainTransfer.network == TRC20)
    ).all()
    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == user.id))

    assert result["detected"] == 2
    assert result["credited"] == 0
    assert {item.tx_hash for item in transfers} == {f"{tx_hash}:0", f"{tx_hash}:1"}
    assert all(item.status == "quarantined" for item in transfers)
    assert wallet.available == Decimal("0")


def test_nine_level_referral_schedule_totals_21_percent_and_is_idempotent():
    dbs = session()
    users = []
    for index in range(10):
        user = User(
            email=f"nine-level-{index}@example.com",
            password_hash="test",
            referral_code=f"NINE{index}",
            status="active",
            kyc_status="verified",
        )
        dbs.add(user)
        dbs.flush()
        users.append(user)

    # users[0] is level 1; users[9] is the depositing member.
    for parent, child in zip(users[:-1], users[1:]):
        dbs.add(Referral(referrer_user_id=parent.id, referred_user_id=child.id))
    dbs.flush()

    first = accrue_referral_commissions(
        dbs,
        depositing_user_id=users[9].id,
        deposit_amount=Decimal("100"),
        source_reference="DEP-NINE-LEVEL",
    )
    duplicate = accrue_referral_commissions(
        dbs,
        depositing_user_id=users[9].id,
        deposit_amount=Decimal("100"),
        source_reference="DEP-NINE-LEVEL",
    )
    dbs.commit()

    expected = [
        Decimal("10"), Decimal("3"), Decimal("2"), Decimal("1"),
        Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1"), Decimal("1"),
    ]
    assert [Decimal(item["amount"]) for item in first] == expected
    assert sum((Decimal(item["amount"]) for item in first), Decimal("0")) == Decimal("21")
    assert [int(item["level"]) for item in first] == list(range(1, 10))
    assert duplicate == []
    pending_entries = dbs.scalars(
        select(LedgerEntry).where(LedgerEntry.kind == "referral_bonus")
    ).all()
    assert len(pending_entries) == 9
    assert all(item.status == "pending" for item in pending_entries)


def test_tron_scan_is_disabled_without_explicit_opt_in(monkeypatch):
    dbs = session()
    monkeypatch.delenv("ASTER_TRON_ENABLED", raising=False)

    def unexpected_http(*args, **kwargs):
        raise AssertionError("TRON network must not be called while disabled")

    monkeypatch.setattr(blockchain, "http_json", unexpected_http)
    result = blockchain.tron_scan(dbs)
    assert result["status"] == "not_configured"
    assert result["detected"] == 0
    assert result["credited"] == 0

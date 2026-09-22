import os
os.environ["ASTER_SKIP_CREATE_ALL"] = "true"

from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app import blockchain
from app.funding import BlockchainCursor, BlockchainTransfer, DepositIntent
from app.main import AuditEvent, Base, User, Wallet
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
    assert treasury_address(BEP20) == "0xAf37c145EE58C0C0bD281BF454Ee92beC93F13d5"
    assert treasury_address(TRC20) == "TMrK4d1r2cGye2TwX3JfjCaUDWvZy6aoXD"


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
    )
    dbs.add(intent)
    dbs.flush()

    transfer = BlockchainTransfer(
        network=BEP20,
        tx_hash="0xabc:0",
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
    ))
    dbs.flush()

    sender = "1" * 40
    recipient = treasury_address(BEP20)[2:].lower()
    amount_hex = hex(12_50000000 * 10**10)
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

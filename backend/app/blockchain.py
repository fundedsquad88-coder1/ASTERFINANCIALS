"""Aster blockchain deposit watcher.

Sandbox-first watcher for USDT on BSC BEP20 and TRON TRC20.
No private keys are used by this service.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.funding import BlockchainCursor, BlockchainTransfer, DepositIntent, LedgerEntry
from app.main import AuditEvent, Wallet, post_double_entry
from app.treasury import BEP20, TRC20, treasury_address

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a6e0c22e2c"
DEFAULT_BSC_USDT = "0x55d398326f99059fF775485246999027B3197955"
DEFAULT_TRON_USDT = "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"

def http_json(url: str, payload: dict | None = None, headers: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=int(os.getenv("ASTER_CHAIN_HTTP_TIMEOUT", "15"))) as response:
        return json.loads(response.read().decode())

def bsc_config() -> dict:
    return {
        "rpc": os.getenv("ASTER_BSC_RPC_URL", "").strip(),
        "usdt": os.getenv("ASTER_BSC_USDT_CONTRACT", DEFAULT_BSC_USDT).strip(),
        "confirmations": max(1, int(os.getenv("ASTER_BSC_CONFIRMATIONS", "12"))),
        "batch": max(1, int(os.getenv("ASTER_BSC_LOG_BATCH", "2000"))),
        "start_block": max(0, int(os.getenv("ASTER_BSC_START_BLOCK", "0"))),
    }

def tron_config() -> dict:
    return {
        "api": os.getenv("ASTER_TRON_API_URL", "https://api.trongrid.io").rstrip("/"),
        "api_key": os.getenv("ASTER_TRON_API_KEY", "").strip(),
        "usdt": os.getenv("ASTER_TRON_USDT_CONTRACT", DEFAULT_TRON_USDT).strip(),
        "confirmations": max(1, int(os.getenv("ASTER_TRON_CONFIRMATIONS", "1"))),
        "start_ms": max(0, int(os.getenv("ASTER_TRON_START_MS", "0"))),
        "limit": max(1, min(200, int(os.getenv("ASTER_TRON_PAGE_SIZE", "200")))),
    }

def _hex_block(value: int) -> str:
    return hex(value)

def _topic_address(address: str) -> str:
    return "0x" + ("0" * 24) + address[2:].lower()

def bsc_scan(dbs: Session) -> dict:
    cfg = bsc_config()
    if not cfg["rpc"]:
        return {"network": BEP20, "status": "not_configured", "message": "ASTER_BSC_RPC_URL is not configured."}

    treasury = treasury_address(BEP20).lower()
    cursor = dbs.scalar(select(BlockchainCursor).where(BlockchainCursor.network == BEP20))
    if not cursor:
        cursor = BlockchainCursor(network=BEP20, cursor=cfg["start_block"])
        dbs.add(cursor)
        dbs.flush()

    latest = int(http_json(cfg["rpc"], {"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []})["result"], 16)
    finalized_result = http_json(
        cfg["rpc"],
        {"jsonrpc": "2.0", "id": 2, "method": "eth_getBlockByNumber", "params": ["finalized", False]},
    )
    finalized_hex = (finalized_result.get("result") or {}).get("number")
    finalized = int(finalized_hex, 16) if finalized_hex else 0
    safe_head = finalized if finalized else max(0, latest - cfg["confirmations"])

    if cursor.cursor >= safe_head:
        return {"network": BEP20, "status": "idle", "cursor": cursor.cursor, "safe_head": safe_head, "detected": 0, "credited": 0}

    start = cursor.cursor + 1
    end = min(safe_head, cursor.cursor + cfg["batch"])
    logs_result = http_json(
        cfg["rpc"],
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": _hex_block(start),
                "toBlock": _hex_block(end),
                "address": cfg["usdt"],
                "topics": [TRANSFER_TOPIC, None, _topic_address(treasury)],
            }],
        },
    )
    logs = logs_result.get("result", [])
    if not isinstance(logs, list):
        raise RuntimeError("BSC RPC returned an invalid log response")

    detected = credited = 0
    for log in logs:
        topics = log.get("topics", [])
        if len(topics) < 3 or not log.get("transactionHash") or not log.get("blockNumber"):
            continue
        tx_hash = str(log["transactionHash"])
        log_index = int(log.get("logIndex", "0x0"), 16)
        unique = f"{tx_hash}:{log_index}"
        if dbs.scalar(select(BlockchainTransfer).where(BlockchainTransfer.tx_hash == unique)):
            continue

        amount = Decimal(int(log.get("data", "0x0"), 16)) / Decimal(10**18)
        block_number = int(log["blockNumber"], 16)
        transfer = BlockchainTransfer(
            network=BEP20,
            tx_hash=unique,
            log_index=log_index,
            block_number=block_number,
            token_contract=cfg["usdt"],
            from_address="0x" + topics[1][-40:],
            to_address="0x" + topics[2][-40:],
            amount=amount,
            confirmations=max(0, safe_head - block_number + 1),
            status="confirmed" if block_number <= safe_head else "detected",
        )
        dbs.add(transfer)
        dbs.flush()
        detected += 1
        if transfer.status == "confirmed" and credit_transfer(dbs, transfer):
            credited += 1

    cursor.cursor = end
    cursor.updated_at = datetime.now(timezone.utc)
    dbs.commit()
    return {
        "network": BEP20, "status": "scanned", "from_block": start,
        "to_block": end, "cursor": cursor.cursor, "safe_head": safe_head,
        "detected": detected, "credited": credited,
    }

def tron_scan(dbs: Session) -> dict:
    cfg = tron_config()
    treasury = treasury_address(TRC20)
    headers = {"TRON-PRO-API-KEY": cfg["api_key"]} if cfg["api_key"] else {}
    cursor = dbs.scalar(select(BlockchainCursor).where(BlockchainCursor.network == TRC20))
    if not cursor:
        cursor = BlockchainCursor(network=TRC20, cursor=cfg["start_ms"])
        dbs.add(cursor)
        dbs.flush()

    url = (
        f"{cfg['api']}/v1/accounts/{treasury}/transactions/trc20"
        f"?only_confirmed=true&only_to=true&limit={cfg['limit']}"
        f"&order_by=block_timestamp,asc&contract_address={cfg['usdt']}"
    )
    if cursor.cursor:
        url += f"&min_timestamp={cursor.cursor + 1}"

    payload = http_json(url, headers=headers)
    rows = payload.get("data", [])
    if not isinstance(rows, list):
        raise RuntimeError("TRON API returned an invalid transaction response")

    detected = credited = 0
    newest = cursor.cursor
    for row in rows:
        ts = int(row.get("block_timestamp", 0))
        newest = max(newest, ts)
        tx_hash = str(row.get("transaction_id", ""))
        if not tx_hash or dbs.scalar(select(BlockchainTransfer).where(BlockchainTransfer.tx_hash == tx_hash)):
            continue

        token_contract = str(row.get("token_info", {}).get("address", ""))
        if token_contract.lower() != cfg["usdt"].lower():
            continue

        to_address = str(row.get("to", ""))
        if to_address != treasury:
            continue

        amount = Decimal(str(row.get("value", "0"))) / Decimal(10**6)
        transfer = BlockchainTransfer(
            network=TRC20,
            tx_hash=tx_hash,
            log_index=None,
            block_number=int(row.get("block", 0) or 0),
            token_contract=token_contract,
            from_address=str(row.get("from", "")),
            to_address=to_address,
            amount=amount,
            confirmations=cfg["confirmations"],
            status="confirmed",
        )
        dbs.add(transfer)
        dbs.flush()
        detected += 1
        if credit_transfer(dbs, transfer):
            credited += 1

    cursor.cursor = newest
    cursor.updated_at = datetime.now(timezone.utc)
    dbs.commit()
    return {"network": TRC20, "status": "scanned", "cursor_ms": cursor.cursor, "detected": detected, "credited": credited}

def credit_transfer(dbs: Session, transfer: BlockchainTransfer) -> bool:
    if transfer.status != "confirmed":
        return False

    pending = dbs.scalars(
        select(DepositIntent).where(
            DepositIntent.network == transfer.network,
            DepositIntent.currency == "USDT",
            DepositIntent.status == "pending",
            DepositIntent.deposit_address == treasury_address(transfer.network),
            DepositIntent.amount == transfer.amount,
        )
    ).all()

    if len(pending) != 1:
        transfer.status = "quarantined"
        dbs.add(AuditEvent(
            user_id=None,
            event_type="deposit_quarantined",
            metadata_json=json.dumps({
                "transfer_id": transfer.id,
                "network": transfer.network,
                "amount": str(transfer.amount),
                "tx_hash": transfer.tx_hash,
                "reason": "no_unique_matching_intent",
            }),
        ))
        return False

    intent = pending[0]
    wallet = dbs.scalar(select(Wallet).where(Wallet.user_id == intent.user_id).with_for_update())
    if not wallet:
        raise RuntimeError("Wallet not found for deposit intent")

    reference = "DEP-CHAIN-" + transfer.tx_hash.replace(":", "-")
    post_double_entry(
        dbs,
        user_id=intent.user_id,
        reference=reference,
        amount=transfer.amount,
        debit_account="user.available",
        credit_account="platform.funding",
    )
    wallet.available += transfer.amount
    intent.status = "confirmed"
    transfer.deposit_intent_id = intent.id
    transfer.status = "credited"
    transfer.credited_at = datetime.now(timezone.utc)
    dbs.add(LedgerEntry(
        user_id=intent.user_id, kind="deposit", amount=transfer.amount,
        reference=reference, currency="USDT", status="posted",
    ))
    dbs.add(AuditEvent(
        user_id=intent.user_id,
        event_type="blockchain_deposit_credited",
        metadata_json=json.dumps({
            "network": transfer.network, "tx_hash": transfer.tx_hash,
            "amount": str(transfer.amount),
        }),
    ))
    return True

def scan_once(dbs: Session) -> dict:
    return {"bep20": bsc_scan(dbs), "trc20": tron_scan(dbs)}

"""Aster blockchain deposit watcher.

Sandbox-first watcher for USDT on BSC BEP20 and TRON TRC20.
It only credits a user after:
1) the transfer is observed on the configured chain,
2) it targets Aster's configured treasury address,
3) the token contract matches the configured USDT contract,
4) the transaction reaches the configured confirmation threshold,
5) exactly one pending deposit intent matches network + expected amount.

No private keys are used by this service.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.funding import BlockchainCursor, BlockchainTransfer, DepositIntent, LedgerEntry
from app.main import AuditEvent, Wallet, post_double_entry
from app.treasury import BEP20, TRC20, NETWORKS, treasury_address

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a6e0c22e2c"
DEFAULT_BSC_USDT = "0x55d398326f99059fF775485246999027B3197955"
DEFAULT_TRON_USDT = "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"

def env_bool(name: str, default=False):
    return os.getenv(name, str(default)).lower() in ("1","true","yes","on")

def http_json(url: str, payload: dict | None = None, headers: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type":"application/json", **(headers or {})}, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=int(os.getenv("ASTER_CHAIN_HTTP_TIMEOUT","15"))) as r:
        return json.loads(r.read().decode())

def bsc_config():
    return {
        "rpc": os.getenv("ASTER_BSC_RPC_URL","").strip(),
        "usdt": os.getenv("ASTER_BSC_USDT_CONTRACT", DEFAULT_BSC_USDT).strip(),
        "confirmations": int(os.getenv("ASTER_BSC_CONFIRMATIONS","12")),
        "batch": int(os.getenv("ASTER_BSC_LOG_BATCH","2000")),
    }

def tron_config():
    return {
        "api": os.getenv("ASTER_TRON_API_URL","https://api.trongrid.io").rstrip("/"),
        "api_key": os.getenv("ASTER_TRON_API_KEY","").strip(),
        "usdt": os.getenv("ASTER_TRON_USDT_CONTRACT", DEFAULT_TRON_USDT).strip(),
        "confirmations": int(os.getenv("ASTER_TRON_CONFIRMATIONS","1")),
    }

def _hex_block(v: int) -> str: return hex(v)

def bsc_scan(dbs: Session) -> dict:
    cfg=bsc_config()
    if not cfg["rpc"]:
        return {"network":BEP20,"status":"not_configured","message":"ASTER_BSC_RPC_URL is not configured."}
    treasury=treasury_address(BEP20).lower()
    cursor=dbs.scalar(select(BlockchainCursor).where(BlockchainCursor.network==BEP20))
    if not cursor:
        cursor=BlockchainCursor(network=BEP20,cursor=int(os.getenv("ASTER_BSC_START_BLOCK","0"))); dbs.add(cursor); dbs.flush()
    latest=int(http_json(cfg["rpc"],{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]})["result"],16)
    finalized_res=http_json(cfg["rpc"],{"jsonrpc":"2.0","id":2,"method":"eth_getBlockByNumber","params":["finalized",False]})
    finalized=int(finalized_res.get("result",{}).get("number","0x0"),16)
    safe_head=max(0, finalized if finalized else latest-cfg["confirmations"])
    if cursor.cursor>=safe_head: return {"network":BEP20,"status":"idle","cursor":cursor.cursor,"safe_head":safe_head,"detected":0,"credited":0}
    end=min(safe_head,cursor.cursor+cfg["batch"])
    padded_to="0x"+"0"*24+treasury[2:]
    logs=http_json(cfg["rpc"],{"jsonrpc":"2.0","id":3,"method":"eth_getLogs","params":[{"fromBlock":_hex_block(cursor.cursor+1),"toBlock":_hex_block(end),"address":cfg["usdt"],"topics":[TRANSFER_TOPIC,None,padded_to]}]})["result"]
    detected=credited=0
    for log in logs:
        tx=str(log["transactionHash"]); idx=int(log.get("logIndex","0x0"),16); unique=f"{tx}:{idx}"
        if dbs.scalar(select(BlockchainTransfer).where(BlockchainTransfer.tx_hash==unique)): continue
        data=log.get("data","0x")
        amount=Decimal(int(data,16))/Decimal(10**18)
        from_addr="0x"+log["topics"][1][-40:]
        to_addr="0x"+log["topics"][2][-40:]
        transfer=BlockchainTransfer(network=BEP20,tx_hash=unique,log_index=idx,block_number=int(log["blockNumber"],16),token_contract=cfg["usdt"],from_address=from_addr,to_address=to_addr,amount=amount,confirmations=max(0,safe_head-int(log["blockNumber"],16)+1),status="confirmed" if int(log["blockNumber"],16)<=safe_head else "detected")
        dbs.add(transfer); dbs.flush(); detected+=1
        if transfer.status=="confirmed":
            if credit_transfer(dbs,transfer): credited+=1
    cursor.cursor=end; cursor.updated_at=datetime.now(timezone.utc); dbs.commit()
    return {"network":BEP20,"status":"scanned","from_block":end-(end-(cursor.cursor if False else 0)) if False else None,"to_block":end,"cursor":cursor.cursor,"safe_head":safe_head,"detected":detected,"credited":credited}

def tron_scan(dbs: Session) -> dict:
    cfg=tron_config(); treasury=treasury_address(TRC20)
    headers={"TRON-PRO-API-KEY":cfg["api_key"]} if cfg["api_key"] else {}
    cursor=dbs.scalar(select(BlockchainCursor).where(BlockchainCursor.network==TRC20))
    if not cursor:
        cursor=BlockchainCursor(network=TRC20,cursor=int(os.getenv("ASTER_TRON_START_MS","0"))); dbs.add(cursor); dbs.flush()
    url=f"{cfg['api']}/v1/accounts/{treasury}/transactions/trc20?only_confirmed=true&only_to=true&limit=200&order_by=block_timestamp,asc&contract_address={cfg['usdt']}"
    if cursor.cursor: url += f"&min_timestamp={cursor.cursor+1}"
    payload=http_json(url,headers=headers)
    rows=payload.get("data",[])
    detected=credited=0
    newest=cursor.cursor
    for row in rows:
        ts=int(row.get("block_timestamp",0)); newest=max(newest,ts)
        tx=str(row.get("transaction_id","")); unique=tx
        if not tx or dbs.scalar(select(BlockchainTransfer).where(BlockchainTransfer.tx_hash==unique)): continue
        amount=Decimal(str(row.get("value","0")))/Decimal(10**6)
        transfer=BlockchainTransfer(network=TRC20,tx_hash=unique,log_index=None,block_number=int(row.get("block",0) or 0),token_contract=str(row.get("token_info",{}).get("address",cfg["usdt"])),from_address=str(row.get("from","")),to_address=str(row.get("to","")),amount=amount,confirmations=1,status="confirmed")
        dbs.add(transfer); dbs.flush(); detected+=1
        if credit_transfer(dbs,transfer): credited+=1
    cursor.cursor=newest; cursor.updated_at=datetime.now(timezone.utc); dbs.commit()
    return {"network":TRC20,"status":"scanned","cursor_ms":cursor.cursor,"detected":detected,"credited":credited}

def credit_transfer(dbs: Session, transfer: BlockchainTransfer) -> bool:
    if transfer.status != "confirmed": return False
    pending=dbs.scalars(select(DepositIntent).where(DepositIntent.network==transfer.network,DepositIntent.status=="pending",DepositIntent.deposit_address==treasury_address(transfer.network),DepositIntent.amount==transfer.amount)).all()
    if len(pending)!=1:
        transfer.status="quarantined"
        dbs.add(AuditEvent(user_id=None,event_type="deposit_quarantined",metadata_json=json.dumps({"transfer_id":transfer.id,"network":transfer.network,"amount":str(transfer.amount),"reason":"no_unique_matching_intent"})))
        return False
    intent=pending[0]
    w=dbs.scalar(select(Wallet).where(Wallet.user_id==intent.user_id).with_for_update())
    if not w: raise RuntimeError("Wallet not found for deposit intent")
    ref="DEP-CHAIN-"+transfer.tx_hash.replace(":","-")
    post_double_entry(dbs,user_id=intent.user_id,reference=ref,amount=transfer.amount,debit_account="user.available",credit_account="platform.funding")
    w.available += transfer.amount
    intent.amount=transfer.amount; intent.status="confirmed"
    transfer.deposit_intent_id=intent.id; transfer.status="credited"; transfer.credited_at=datetime.now(timezone.utc)
    dbs.add(LedgerEntry(user_id=intent.user_id,kind="deposit",amount=transfer.amount,reference=ref,currency="USDT",status="posted"))
    dbs.add(AuditEvent(user_id=intent.user_id,event_type="blockchain_deposit_credited",metadata_json=json.dumps({"network":transfer.network,"tx_hash":transfer.tx_hash,"amount":str(transfer.amount)})))
    return True

def scan_once(dbs: Session) -> dict:
    return {"bep20":bsc_scan(dbs),"trc20":tron_scan(dbs)}

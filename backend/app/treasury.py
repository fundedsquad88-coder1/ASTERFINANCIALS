import os
import re

BEP20 = "BEP20"
TRC20 = "TRC20"

TREASURY_ADDRESSES = {
    BEP20: os.getenv("ASTER_TREASURY_BEP20_ADDRESS", "0xAf37c145EE58C0C0bD281BF454Ee92beC93F13d5").strip(),
    TRC20: os.getenv("ASTER_TREASURY_TRC20_ADDRESS", "TMrK4d1r2cGye2TwX3JfjCaUDWvZy6aoXD").strip(),
}

NETWORKS = {
    BEP20: {"name": "BNB Smart Chain", "label": "USDT · BEP20", "chain_id": 56, "decimals": 18, "address": TREASURY_ADDRESSES[BEP20]},
    TRC20: {"name": "Tron", "label": "USDT · TRC20", "chain_id": None, "decimals": 6, "address": TREASURY_ADDRESSES[TRC20]},
}

def normalize_network(value: str) -> str:
    raw = (value or "").strip().upper().replace("-", "").replace("_", "").replace(" ", "")
    return {"BEP20": BEP20, "BSC": BEP20, "BNBSMARTCHAIN": BEP20, "TRC20": TRC20, "TRON": TRC20}.get(raw, "")

def treasury_address(network: str) -> str:
    normalized = normalize_network(network)
    if normalized not in TREASURY_ADDRESSES:
        raise ValueError("Unsupported USDT network")
    address = TREASURY_ADDRESSES[normalized]
    if not valid_address(normalized, address):
        raise ValueError(f"Invalid configured treasury address for {normalized}")
    return address

def valid_address(network: str, address: str) -> bool:
    normalized = normalize_network(network)
    value = (address or "").strip()
    if normalized == BEP20:
        return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", value))
    if normalized == TRC20:
        return bool(re.fullmatch(r"T[1-9A-HJ-NP-Za-km-z]{33}", value))
    return False

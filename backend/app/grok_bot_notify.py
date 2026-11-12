"""Optional notification helper for Grok Bot integration.

Sends small JSON payloads to a Grok Bot webhook so the Bot can ask the owner
for approval on withdrawals or help review deposits.

This module never holds private keys and never sends funds.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _webhook_url() -> str:
    return os.getenv("ASTER_GROK_BOT_WEBHOOK_URL", "").strip()


def _secret() -> str:
    return os.getenv("ASTER_GROK_BOT_SECRET", "").strip()


def _post(payload: dict[str, Any]) -> dict[str, Any]:
    """Best-effort POST. Failures never block the main API."""
    url = _webhook_url()
    if not url:
        return {"sent": False, "reason": "ASTER_GROK_BOT_WEBHOOK_URL not configured"}

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AsterFinancials-GrokNotify/1.0",
    }
    secret = _secret()
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
        headers["X-Aster-Grok-Secret"] = secret

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return {"sent": True, "status_code": getattr(resp, "status", 200)}
    except urllib.error.HTTPError as exc:
        return {"sent": False, "reason": f"http_{exc.code}", "detail": str(exc.reason)}
    except Exception as exc: # intentional broad catch
        return {"sent": False, "reason": "network_error", "detail": str(exc)[:200]}


def notify_new_withdrawal(payload: dict[str, Any]) -> dict[str, Any]:
    payload = {"event": "withdrawal.requested", **payload}
    return _post(payload)


def notify_deposit_review(payload: dict[str, Any]) -> dict[str, Any]:
    payload = {"event": "deposit.needs_review", **payload}
    return _post(payload)

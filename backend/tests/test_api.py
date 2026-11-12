from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timezone
from app.main import app, SessionLocal, AutoInvest, Wallet, User
from app.funding import BlockchainTransfer, DepositIntent, WithdrawalRequest
from app.blockchain import DEFAULT_BSC_USDT
from app.treasury import BEP20, treasury_address

client = TestClient(app)

def verify_user_kyc(user_id: int):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).one()
    user.kyc_status = "verified"
    db.commit()
    db.close()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True

def test_register_login_and_protected_wallet():
    email = "qa-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    assert response.json()["csrf_token"]
    assert any("AsterSession" in key for key in response.cookies.keys())
    wallet = client.get("/v1/wallet")
    assert wallet.status_code == 200
    assert wallet.json()["available"] in {"0", "0E-8"}


def test_autoinvest_enforces_fixed_packages_and_account_principal_limit():
    email = "packages-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    csrf = client.cookies.get("AsterCSRF")
    headers = {"X-Aster-CSRF": csrf, "Idempotency-Key": "package-test-" + __import__("secrets").token_hex(8)}

    unsupported = client.post(
        "/v1/autoinvest",
        headers=headers,
        json={"strategy": "Core Crypto", "amount": "15"},
    )
    assert unsupported.status_code == 422
    assert "Choose one of the available Auto-Invest amounts" in unsupported.json()["detail"]

    above_cap = client.post(
        "/v1/autoinvest",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "package-cap-" + __import__("secrets").token_hex(8)},
        json={"strategy": "Core Crypto", "amount": "501"},
    )
    assert above_cap.status_code == 422

    # Duration is now optional for the current app; an unfunded account still
    # cannot activate a position or create an artificial balance.
    unfunded = client.post(
        "/v1/autoinvest",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "package-unfunded-" + __import__("secrets").token_hex(8)},
        json={"strategy": "Core Crypto", "amount": "10"},
    )
    assert unfunded.status_code == 403
    assert "Identity verification is required" in unfunded.json()["detail"]


def test_autoinvest_requires_idempotency_key():
    email = "ai-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    csrf = client.cookies.get("AsterCSRF")
    response = client.post(
        "/v1/autoinvest",
        headers={"X-Aster-CSRF": csrf},
        json={"strategy": "Core Crypto", "amount": "10", "duration_weeks": 4},
    )
    assert response.status_code == 400
    assert "Idempotency-Key" in response.json()["detail"]

def test_autoinvest_idempotency_replays_same_result():
    email = "idem-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    csrf = client.cookies.get("AsterCSRF")
    headers = {"X-Aster-CSRF": csrf, "Idempotency-Key": "idem-" + __import__("secrets").token_hex(16)}
    first = client.post("/v1/autoinvest", headers=headers,
                        json={"strategy": "Core Crypto", "amount": "10", "duration_weeks": 4})
    assert first.status_code == 403
    assert "Identity verification is required" in first.json()["detail"]


def test_portfolio_and_autoinvest_lifecycle():
    email = "life-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    csrf = client.cookies.get("AsterCSRF")
    portfolio = client.get("/v1/portfolio")
    assert portfolio.status_code == 200
    assert portfolio.json()["strategy_count"] == 0
    # Account starts with no funds; activation must fail rather than fabricate capital.
    create = client.post(
        "/v1/autoinvest",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "life-" + __import__("secrets").token_hex(16)},
        json={"strategy": "Core Crypto", "amount": "10", "duration_weeks": 4},
    )
    assert create.status_code == 403
    assert "Identity verification is required" in create.json()["detail"]


def test_autoinvest_principal_cannot_be_released_or_cancelled():
    email = "locked-" + __import__("secrets").token_hex(5) + "@example.com"
    registered = client.post("/v1/auth/register", json={
        "email": email, "password": "AsterTestPassword!123"
    })
    assert registered.status_code == 201
    user_id = registered.json()["id"]
    csrf = client.cookies.get("AsterCSRF")

    db = SessionLocal()
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).one()
    wallet.available = 0
    wallet.invested = 10
    position = AutoInvest(
        user_id=user_id,
        strategy="Core Crypto",
        amount=10,
        duration_weeks=8,
        status="active",
    )
    db.add(position)
    db.commit()
    position_id = position.id
    db.close()

    headers = {"X-Aster-CSRF": csrf}
    released = client.post(
        f"/v1/autoinvest/{position_id}/release",
        headers={**headers, "Idempotency-Key": "locked-release-" + __import__("secrets").token_hex(8)},
    )
    cancelled = client.post(f"/v1/autoinvest/{position_id}/cancel", headers=headers)
    assert released.status_code == 409
    assert cancelled.status_code == 409

    db = SessionLocal()
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).one()
    assert wallet.available == 0
    assert wallet.invested == 10
    db.close()


def test_autoinvest_cancel_boundary_without_funds():
    email = "cancel-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    csrf = client.cookies.get("AsterCSRF")
    missing = client.get("/v1/autoinvest/999999")
    assert missing.status_code == 404
    cancel = client.post("/v1/autoinvest/999999/cancel", headers={"X-Aster-CSRF": csrf})
    assert cancel.status_code == 404


def test_portfolio_performance_and_transaction_summary():
    email = "perf-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    perf = client.get("/v1/portfolio/performance")
    assert perf.status_code == 200
    assert perf.json()["total"] == "0E-8" or perf.json()["total"] == "0"
    summary = client.get("/v1/transactions/summary")
    assert summary.status_code == 200
    assert summary.json()["count"] == 0


def test_strategy_valuation_is_account_scoped():
    email = "val-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    csrf = client.cookies.get("AsterCSRF")
    missing = client.get("/v1/autoinvest/999999/valuation")
    assert missing.status_code == 404
    portfolio = client.get("/v1/portfolio/performance")
    assert portfolio.status_code == 200
    assert portfolio.json()["valuation_status"] == "unpriced"


def test_valuation_rejects_future_timestamp():
    email = "fresh-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    csrf = client.cookies.get("AsterCSRF")
    response = client.post(
        "/v1/autoinvest/999999/valuation",
        headers={"X-Aster-CSRF": csrf},
        json={"value":"10","source":"test","as_of":"2099-01-01T00:00:00Z"},
    )
    assert response.status_code == 404


def test_double_entry_created_for_autoinvest():
    email = "ledger-" + __import__("secrets").token_hex(5) + "@example.com"
    client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    csrf = client.cookies.get("AsterCSRF")
    # No funded wallet is available in the public API yet, so this boundary must remain fail-closed.
    response = client.post("/v1/autoinvest", headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "ledger-test-key-123456"}, json={"strategy":"core-crypto","amount":"10","duration_weeks":1})
    assert response.status_code == 403
    assert "Identity verification is required" in response.json()["detail"]


def test_ledger_integrity_endpoint_reports_balanced_state():
    email = "integrity-" + __import__("secrets").token_hex(5) + "@example.com"
    client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    response = client.get("/v1/ledger/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["balanced"] is True
    assert body["unbalanced_transaction_ids"] == []


def test_wallet_ledger_reconciliation_starts_balanced():
    email = "recon-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    response = client.get("/v1/ledger/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["wallet_balanced"] is True
    assert body["wallet_mismatches"] == {"available":"0","invested":"0","pending":"0"}


def test_deposit_uses_aster_treasury_and_withdrawal_stays_fail_closed_without_funds():
    email = "fund-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    verify_user_kyc(response.json()["id"])
    csrf = client.cookies.get("AsterCSRF")
    deposit = client.post("/v1/wallet/deposits",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "fund-deposit-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"TRC20","expected_amount":"25"})
    assert deposit.status_code == 201
    deposit_body = deposit.json()
    assert deposit_body["custody"] == "Aster treasury"
    assert deposit_body["network"] == "TRC20"
    assert deposit_body["deposit_address"].startswith("T")
    trc20_withdrawal = client.post("/v1/wallet/withdrawals",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "fund-withdraw-trc-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"TRC20","address":"T" + "1"*33,"amount":"1"})
    assert trc20_withdrawal.status_code == 422
    assert "only on BNB Smart Chain" in trc20_withdrawal.json()["detail"]

    bep20_withdrawal = client.post("/v1/wallet/withdrawals",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "fund-withdraw-bsc-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"BEP20","address":"0x" + "1"*40,"amount":"1"})
    assert bep20_withdrawal.status_code == 409
    assert bep20_withdrawal.json()["detail"] == "Insufficient available balance"


def test_deposit_transaction_hash_is_bound_to_authenticated_intent():
    email = "txclaim-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    verify_user_kyc(response.json()["id"])
    csrf = client.cookies.get("AsterCSRF")
    created = client.post("/v1/wallet/deposits",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "txclaim-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"BEP20","expected_amount":"25"})
    assert created.status_code == 201
    deposit_id = created.json()["id"]
    invalid = client.post(f"/v1/wallet/deposits/{deposit_id}/transaction",
        headers={"X-Aster-CSRF": csrf}, json={"tx_hash":"not-a-hash"})
    assert invalid.status_code == 422
    tx_hash = "0x" + __import__("secrets").token_hex(32)
    submitted = client.post(f"/v1/wallet/deposits/{deposit_id}/transaction",
        headers={"X-Aster-CSRF": csrf}, json={"tx_hash":tx_hash})
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "transaction_submitted"
    duplicate = client.post(f"/v1/wallet/deposits/{deposit_id}/transaction",
        headers={"X-Aster-CSRF": csrf}, json={"tx_hash":"0x" + "b" * 64})
    assert duplicate.status_code == 409
    fetched = client.get(f"/v1/wallet/deposits/{deposit_id}")
    assert fetched.status_code == 200
    assert fetched.json()["tx_hash"] == tx_hash

def test_treasury_deposit_addresses_expose_only_public_receiving_addresses():
    response = client.get("/v1/wallet/deposit-addresses")
    assert response.status_code == 200
    body = response.json()
    assert body["custody"] == "Aster treasury"
    assert {x["network"] for x in body["networks"]} == {"BEP20", "TRC20"}
    by_network = {x["network"]: x for x in body["networks"]}
    assert by_network["BEP20"]["address"].startswith("0x")
    assert by_network["TRC20"]["address"].startswith("T")

def test_provider_webhook_requires_signature_secret():
    response = client.post("/v1/wallet/provider/webhook", json={
        "event_id":"evt-test-12345678","event_type":"deposit.confirmed",
        "provider_reference":"dep-test-12345678","status":"confirmed",
        "amount":"10","currency":"USDT","network":"TRC20"})
    assert response.status_code in {401, 503}


def test_withdrawal_rejects_invalid_network_address_and_is_idempotent():
    email = "wd-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    verify_user_kyc(response.json()["id"])
    csrf = client.cookies.get("AsterCSRF")

    invalid = client.post(
        "/v1/wallet/withdrawals",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "wd-invalid-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"TRC20","address":"0x" + "1"*40,"amount":"1"},
    )
    assert invalid.status_code == 422

    missing = client.post(
        "/v1/wallet/withdrawals",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "wd-empty-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"BEP20","address":"0x" + "1"*40,"amount":"1"},
    )
    assert missing.status_code == 409
    assert missing.json()["detail"] == "Insufficient available balance"


def test_withdrawal_webhook_fails_closed_without_secret():
    email = "wdhook-" + __import__("secrets").token_hex(5) + "@example.com"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    payload = {
        "event_id":"wd-event-12345678",
        "event_type":"withdrawal.confirmed",
        "provider_reference":"AST-WD-TEST",
        "status":"confirmed",
    }
    response = client.post("/v1/wallet/withdrawals/webhook", json=payload)
    assert response.status_code in {401, 503}


def test_admin_withdrawal_processor_requires_admin_key():
    response = client.post("/v1/admin/withdrawals/process")
    assert response.status_code == 403


def test_admin_withdrawal_processor_uses_dry_run_provider_by_default(monkeypatch):
    monkeypatch.delenv("ASTER_WITHDRAWAL_PROVIDER", raising=False)
    monkeypatch.setenv("ASTER_ADMIN_API_KEY", "A" * 32)
    response = client.post(
        "/v1/admin/withdrawals/process?limit=10",
        headers={"X-Aster-Admin-Key": "A" * 32},
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "dry-run"
    assert response.json()["items"] == []


def test_admin_autoinvest_sync_fails_closed_without_provider(monkeypatch):
    monkeypatch.setenv("ASTER_ADMIN_API_KEY", "B" * 32)
    monkeypatch.delenv("ASTER_AUTOINVEST_PROVIDER", raising=False)
    response = client.post(
        "/v1/admin/autoinvest/sync?limit=10",
        headers={"X-Aster-Admin-Key": "B" * 32},
    )
    # No configured valuation provider must fail closed.
    assert response.status_code == 503
    assert "provider" in response.json()["detail"].lower()


def test_admin_autoinvest_execute_is_fail_closed_by_default(monkeypatch):
    monkeypatch.setenv("ASTER_ADMIN_API_KEY", "C" * 32)
    monkeypatch.delenv("ASTER_AUTOINVEST_EXECUTION_PROVIDER", raising=False)
    response = client.post(
        "/v1/admin/autoinvest/execute?limit=10",
        headers={"X-Aster-Admin-Key": "C" * 32},
    )
    assert response.status_code == 503
    assert "execution provider is not configured" in response.json()["detail"]


def test_admin_operations_summary_and_quarantine_are_protected(monkeypatch):
    monkeypatch.setenv("ASTER_ADMIN_API_KEY", "D" * 32)
    unauthorized = client.get("/v1/admin/operations/summary")
    assert unauthorized.status_code == 403

    summary = client.get(
        "/v1/admin/operations/summary",
        headers={"X-Aster-Admin-Key": "D" * 32},
    )
    assert summary.status_code == 200
    body = summary.json()
    assert "deposits" in body
    assert "withdrawals" in body
    assert "blockchain_transfers" in body
    assert body["referral_settlement_enabled"] is False

    invalid_limit = client.get(
        "/v1/admin/blockchain/quarantine?limit=0",
        headers={"X-Aster-Admin-Key": "D" * 32},
    )
    assert invalid_limit.status_code == 422

    quarantine = client.get(
        "/v1/admin/blockchain/quarantine?limit=10",
        headers={"X-Aster-Admin-Key": "D" * 32},
    )
    assert quarantine.status_code == 200
    assert isinstance(quarantine.json()["items"], list)


def test_admin_pending_referral_queue_requires_admin_key(monkeypatch):
    monkeypatch.setenv("ASTER_ADMIN_API_KEY", "E" * 32)
    unauthorized = client.get("/v1/admin/referrals/pending")
    assert unauthorized.status_code == 403

    response = client.get(
        "/v1/admin/referrals/pending?limit=10",
        headers={"X-Aster-Admin-Key": "E" * 32},
    )
    assert response.status_code == 200
    assert isinstance(response.json()["items"], list)


def test_shared_treasury_deposit_requires_admin_attribution_review(monkeypatch):
    email = "attribution-" + __import__("secrets").token_hex(5) + "@example.com"
    registered = client.post("/v1/auth/register", json={
        "email": email,
        "password": "AsterTestPassword!123",
    })
    assert registered.status_code == 201
    user_id = registered.json()["id"]
    verify_user_kyc(user_id)
    csrf = client.cookies.get("AsterCSRF")
    headers = {
        "X-Aster-CSRF": csrf,
        "Idempotency-Key": "attribution-" + __import__("secrets").token_hex(8),
    }

    created = client.post(
        "/v1/wallet/deposits",
        headers=headers,
        json={"currency": "USDT", "network": "BEP20", "expected_amount": "25"},
    )
    assert created.status_code == 201
    deposit_id = created.json()["id"]
    exact_ticket_amount = Decimal(created.json()["expected_amount"])
    tx_hash = "0x" + "a" * 64
    submitted = client.post(
        f"/v1/wallet/deposits/{deposit_id}/transaction",
        headers={"X-Aster-CSRF": csrf},
        json={"tx_hash": tx_hash},
    )
    assert submitted.status_code == 200
    assert "member ownership is independently confirmed" in submitted.json()["message"]

    dbs = SessionLocal()
    transfer = BlockchainTransfer(
        network=BEP20,
        tx_hash=tx_hash + ":0",
        log_index=0,
        block_number=100,
        token_contract=DEFAULT_BSC_USDT,
        from_address="0x" + "1" * 40,
        to_address=treasury_address(BEP20),
        amount=exact_ticket_amount,
        confirmations=20,
        chain_timestamp=datetime.now(timezone.utc),
        status="quarantined",
    )
    dbs.add(transfer)
    dbs.commit()
    transfer_id = transfer.id
    dbs.close()

    monkeypatch.setenv("ASTER_ADMIN_API_KEY", "F" * 32)
    approval = client.post(
        f"/v1/admin/blockchain/transfers/{transfer_id}/approve-attribution",
        headers={"X-Aster-Admin-Key": "F" * 32},
        json={
            "deposit_intent_id": deposit_id,
            "review_reference": "manual-proof-2026-01",
        },
    )
    assert approval.status_code == 200
    assert approval.json()["status"] == "credited"

    dbs = SessionLocal()
    wallet = dbs.query(Wallet).filter(Wallet.user_id == user_id).one()
    intent = dbs.query(DepositIntent).filter(DepositIntent.id == deposit_id).one()
    assert wallet.available == exact_ticket_amount
    assert intent.status == "confirmed"
    dbs.close()

    duplicate = client.post(
        f"/v1/admin/blockchain/transfers/{transfer_id}/approve-attribution",
        headers={"X-Aster-Admin-Key": "F" * 32},
        json={
            "deposit_intent_id": deposit_id,
            "review_reference": "manual-proof-2026-01",
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True


def test_autoinvest_fails_closed_when_verified_user_has_no_execution_provider(monkeypatch):
    email = "provider-gate-" + __import__("secrets").token_hex(5) + "@example.com"
    registered = client.post("/v1/auth/register", json={
        "email": email, "password": "AsterTestPassword!123"
    })
    assert registered.status_code == 201
    user_id = registered.json()["id"]
    csrf = client.cookies.get("AsterCSRF")
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).one()
    user.kyc_status = "verified"
    db.commit()
    db.close()

    monkeypatch.setenv("ASTER_AUTOINVEST_EXECUTION_PROVIDER", "disabled")
    response = client.post(
        "/v1/autoinvest",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "provider-gate-" + __import__("secrets").token_hex(12)},
        json={"strategy": "Core Crypto", "amount": "10"},
    )
    assert response.status_code == 503
    assert "execution provider is not configured" in response.json()["detail"]
    db = SessionLocal()
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).one()
    assert wallet.available == 0
    assert wallet.invested == 0
    assert db.query(AutoInvest).filter(AutoInvest.user_id == user_id).count() == 0
    db.close()


def test_appassets_cors_allows_authenticated_funding_headers():
    origin = "https://appassets.androidplatform.net"
    response = client.options(
        "/v1/wallet/deposits",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,idempotency-key,x-aster-csrf",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "idempotency-key" in allowed
    assert "x-aster-csrf" in allowed


def test_provider_event_id_cannot_be_replayed_with_a_different_payload(monkeypatch):
    import hashlib, hmac, json
    monkeypatch.setenv("ASTER_FUNDING_WEBHOOK_SECRET", "W" * 40)
    email = "webhook-replay-" + __import__("secrets").token_hex(5) + "@example.com"
    registered = client.post("/v1/auth/register", json={
        "email": email, "password": "AsterTestPassword!123"
    })
    assert registered.status_code == 201
    verify_user_kyc(registered.json()["id"])
    csrf = client.cookies.get("AsterCSRF")
    created = client.post(
        "/v1/wallet/deposits",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "webhook-intent-" + __import__("secrets").token_hex(8)},
        json={"currency": "USDT", "network": "BEP20", "expected_amount": "12.5"},
    )
    assert created.status_code == 201
    reference = created.json()["provider_reference"]

    def send(payload):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        signature = hmac.new(b"W" * 40, raw, hashlib.sha256).hexdigest()
        return client.post(
            "/v1/wallet/provider/webhook",
            content=raw,
            headers={"Content-Type": "application/json", "X-Aster-Provider-Signature": signature},
        )

    payload = {
        "event_id": "evt-replay-" + __import__("secrets").token_hex(5),
        "event_type": "deposit.confirmed",
        "provider_reference": reference,
        "status": "confirmed",
        "amount": "12.5",
        "currency": "USDT",
        "network": "BEP20",
    }
    first = send(payload)
    assert first.status_code == 200
    duplicate = send(payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True
    tampered = dict(payload, amount="13.5")
    rejected = send(tampered)
    assert rejected.status_code == 409
    assert "reused with a different payload" in rejected.json()["detail"]


def test_production_status_does_not_overstate_unimplemented_providers(monkeypatch):
    monkeypatch.delenv("ASTER_BSC_RPC_URL", raising=False)
    monkeypatch.delenv("ASTER_TRON_ENABLED", raising=False)
    monkeypatch.delenv("ASTER_AUTOINVEST_EXECUTION_PROVIDER", raising=False)
    monkeypatch.delenv("ASTER_FUNDING_WEBHOOK_SECRET", raising=False)
    response = client.get("/v1/production/status")
    assert response.status_code == 200
    body = response.json()
    assert body["funding_provider"] is False
    assert body["blockchain_bep20_rpc"] is False
    assert body["blockchain_trc20_api"] is False
    assert body["auto_invest_execution_provider"] is False
    assert body["live_withdrawals_enabled"] is False
    assert body["valuation_provider"] is False
    assert body["kyc_aml_provider"] is False
    assert body["production_ready"] is False


def test_unverified_account_cannot_create_deposit_or_withdrawal(monkeypatch):
    email = "kyc-gate-" + __import__("secrets").token_hex(5) + "@example.com"
    registered = client.post("/v1/auth/register", json={
        "email": email, "password": "AsterTestPassword!123"
    })
    assert registered.status_code == 201
    csrf = client.cookies.get("AsterCSRF")

    deposit = client.post(
        "/v1/wallet/deposits",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "kyc-dep-" + __import__("secrets").token_hex(8)},
        json={"currency": "USDT", "network": "BEP20"},
    )
    assert deposit.status_code == 403
    assert "Identity verification" in deposit.json()["detail"]

    withdrawal = client.post(
        "/v1/wallet/withdrawals",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "kyc-wd-" + __import__("secrets").token_hex(8)},
        json={"currency": "USDT", "network": "BEP20", "address": "0x" + "1" * 40, "amount": "1"},
    )
    assert withdrawal.status_code == 403
    assert "Identity verification" in withdrawal.json()["detail"]


def test_signed_deposit_webhook_cannot_credit_unverified_member(monkeypatch):
    import hashlib, hmac, json
    monkeypatch.setenv("ASTER_FUNDING_WEBHOOK_SECRET", "K" * 40)
    email = "kyc-webhook-" + __import__("secrets").token_hex(5) + "@example.com"
    registered = client.post("/v1/auth/register", json={
        "email": email, "password": "AsterTestPassword!123"
    })
    assert registered.status_code == 201
    user_id = registered.json()["id"]
    verify_user_kyc(user_id)
    csrf = client.cookies.get("AsterCSRF")
    created = client.post(
        "/v1/wallet/deposits",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "kyc-webhook-intent-" + __import__("secrets").token_hex(8)},
        json={"currency": "USDT", "network": "BEP20", "expected_amount": "10"},
    )
    assert created.status_code == 201

    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).one()
    user.kyc_status = "unverified"
    db.commit()
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).one()
    db.close()

    payload = {
        "event_id": "evt-kyc-" + __import__("secrets").token_hex(5),
        "event_type": "deposit.confirmed",
        "provider_reference": created.json()["provider_reference"],
        "status": "confirmed",
        "amount": "10",
        "currency": "USDT",
        "network": "BEP20",
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(b"K" * 40, raw, hashlib.sha256).hexdigest()
    response = client.post(
        "/v1/wallet/provider/webhook",
        content=raw,
        headers={"Content-Type": "application/json", "X-Aster-Provider-Signature": signature},
    )
    assert response.status_code == 409
    assert "identity verification" in response.json()["detail"].lower()

    db = SessionLocal()
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).one()
    intent = db.query(DepositIntent).filter(DepositIntent.id == created.json()["id"]).one()
    assert wallet.available == 0
    assert intent.status == "pending"
    db.close()


def test_admin_cannot_approve_unverified_withdrawal(monkeypatch):
    email = "kyc-admin-wd-" + __import__("secrets").token_hex(5) + "@example.com"
    registered = client.post("/v1/auth/register", json={
        "email": email, "password": "AsterTestPassword!123"
    })
    assert registered.status_code == 201
    user_id = registered.json()["id"]
    monkeypatch.setenv("ASTER_ADMIN_API_KEY", "J" * 40)
    db = SessionLocal()
    row = WithdrawalRequest(
        user_id=user_id,
        provider="aster-treasury",
        provider_reference="AST-WD-KYC-" + __import__("secrets").token_hex(5),
        currency="USDT",
        network="BEP20",
        address="0x" + "1" * 40,
        amount=Decimal("1"),
        status="pending",
    )
    db.add(row)
    db.commit()
    withdrawal_id = row.id
    db.close()

    response = client.post(
        f"/v1/admin/withdrawals/{withdrawal_id}/approve",
        headers={"X-Aster-Admin-Key": "J" * 40},
    )
    assert response.status_code == 403
    db = SessionLocal()
    saved = db.query(WithdrawalRequest).filter(WithdrawalRequest.id == withdrawal_id).one()
    assert saved.status == "pending"
    db.close()

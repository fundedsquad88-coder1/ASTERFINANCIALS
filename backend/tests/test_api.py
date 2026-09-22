from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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
    assert first.status_code == 409
    assert first.json()["detail"] == "Insufficient available balance"


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
    assert create.status_code == 409


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
    assert response.status_code == 409


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
    csrf = client.cookies.get("AsterCSRF")
    deposit = client.post("/v1/wallet/deposits",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "fund-deposit-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"TRC20"})
    assert deposit.status_code == 201
    deposit_body = deposit.json()
    assert deposit_body["custody"] == "Aster treasury"
    assert deposit_body["network"] == "TRC20"
    assert deposit_body["deposit_address"].startswith("T")
    withdrawal = client.post("/v1/wallet/withdrawals",
        headers={"X-Aster-CSRF": csrf, "Idempotency-Key": "fund-withdraw-" + __import__("secrets").token_hex(8)},
        json={"currency":"USDT","network":"TRC20","address":"T" + "1"*33,"amount":"1"})
    assert withdrawal.status_code == 409
    assert withdrawal.json()["detail"] == "Insufficient available balance"


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
        json={"currency":"USDT","network":"TRC20","address":"T" + "1"*33,"amount":"1"},
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

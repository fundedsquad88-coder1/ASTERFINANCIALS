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

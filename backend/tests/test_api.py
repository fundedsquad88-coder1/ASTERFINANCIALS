from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True

def test_register_login_and_protected_wallet():
    email = "qa-" + __import__("secrets").token_hex(5) + "@aster.test"
    response = client.post("/v1/auth/register", json={"email": email, "password": "AsterTestPassword!123"})
    assert response.status_code == 201
    assert "aster" in response.cookies
    wallet = client.get("/v1/wallet")
    assert wallet.status_code == 200
    assert wallet.json()["available"] == "0"

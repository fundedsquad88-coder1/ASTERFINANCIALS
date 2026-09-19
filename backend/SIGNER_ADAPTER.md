# Withdrawal signer adapter contract

The API creates a withdrawal_jobs row after admin approval. A separate signer/custody service consumes queued jobs.

## Request
POST WITHDRAWAL_SIGNER_URL
Headers:
- Content-Type: application/json
- X-Aster-Signature: HMAC-SHA256(body, WITHDRAWAL_SIGNER_HMAC_SECRET)

JSON:
{
  "jobId": "uuid",
  "withdrawalId": "uuid",
  "network": "BEP-20 or TRC-20",
  "destination": "validated address",
  "amount": "net USDT amount",
  "idempotencyKey": "withdrawal:<uuid>"
}

## Success
HTTP 200:
{
  "txHash": "on-chain transaction hash",
  "reference": "custody provider reference"
}

The service must be idempotent by idempotencyKey. It must never return success unless the transaction has actually been signed/broadcast or the provider guarantees the returned transaction hash.

## Security
The signer service owns the private key/HSM/MPC policy. The Android app, website and ordinary Aster API never receive a seed phrase or private key.

Trust Wallet/WalletConnect can be used for interactive signing workflows, but an unattended server-side approval flow requires a signer/custody capability with a secure service boundary.

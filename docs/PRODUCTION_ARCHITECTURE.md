# Aster production architecture

## Money movement
1. Android is a client; PostgreSQL and the API are the source of truth.
2. A user submits a deposit claim with network and TXID. Claimed amount is informational only.
3. The blockchain worker independently verifies USDT transfer, treasury recipient, transaction success/finality and uniqueness.
4. Only a verified transfer creates a posted deposit ledger entry. Unmatched verified transfers remain available for operations reconciliation.
5. Auto-invest moves verified available balance into an investment record. Weekly accounting uses a server-published realized rate; the client cannot create returns.
6. A withdrawal is validated and enters the admin queue. Approval calculates the fee and moves it to processing.
7. Approved withdrawals can be handed to an isolated treasury signer/custody service. The API and Android app never hold a seed phrase/private key.
8. A withdrawal is not complete merely because approval occurred; completion requires the actual outgoing transaction hash.

## Trust Wallet
WalletConnect/deep links are appropriate for connecting a user's wallet to a dApp and requesting a wallet signature. They are not a server-side treasury API for unattended withdrawals. Aster therefore exposes a signer contract in backend/treasury-signer.js rather than embedding a Trust Wallet seed phrase in the application. A dedicated custody/HSM/signer service can implement that contract.

## Required production controls
- Managed PostgreSQL with encrypted backups and point-in-time recovery.
- Separate API and worker processes.
- HTTPS only and a strict CORS_ORIGINS allowlist.
- Secrets stored in the hosting provider secret manager.
- Admin users provisioned in admin_users; use role separation and 2FA at the identity/custody layer.
- Monitor RPC/indexer credentials and rotate them.
- Alerts for worker failures, RPC failures, unmatched transfers, duplicate claims and withdrawal anomalies.
- Never advertise projected investment rates as guaranteed returns.
- Obtain jurisdiction-specific legal/compliance advice before accepting customer funds, including custody, AML/KYC, investment-service and consumer-protection requirements.

## Deployment
API: npm start
Worker: npm run worker
Checks: npm run check

The worker should run as one logical instance. If the hosting platform can run multiple worker replicas, add deployment-level singleton or PostgreSQL advisory-lock leader election before scaling replicas.

## Withdrawal operations
Pending -> Approved/Processing -> signer submission -> on-chain confirmation -> Completed.
Rejected withdrawals are not successful payouts. Keep approval, rejection and execution events in admin_audit_log.

Never commit production secrets or wallet private keys.

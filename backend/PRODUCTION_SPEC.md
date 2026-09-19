# Aster Financials — Production Financial System Specification

## Objective
Server-authoritative USDT funding, investment, ledger, withdrawal and operations system for the Android app and website.

## Source of truth
- PostgreSQL is the financial source of truth.
- Blockchain state is the source of truth for on-chain transfers.
- Clients never calculate or mutate balances.
- Every balance-changing operation creates a ledger record.
- Every on-chain transfer is idempotent by network + transaction hash + transfer index.

## Deposit flow
User selects TRC-20 or BEP-20 -> treasury address -> blockchain watcher -> verify network/token/recipient/amount/finality -> record transfer -> post deposit ledger -> balance updates. A submitted TXID is only a reference; periodic reconciliation also finds deposits when the user did not submit a TXID.

## Investment flow
User chooses crypto or forex. Server checks available balance in a DB transaction, moves funds into the investment, and records principal. Projection percentages are UI projections only. Weekly realized rates are published server-side and applied transactionally and idempotently.

## Withdrawal flow
User submits network, destination and amount. Server validates address and balance, calculates fee, reserves the gross amount, and creates a pending request. Admin sees user, gross amount, fee, net amount, network and destination. Approval creates an execution job. A secure custody/HSM/MPC/signer adapter signs and broadcasts without exposing a private key to Android or the ordinary API server. The resulting TXID is recorded and the chain watcher confirms settlement.

## Trust Wallet
WalletConnect is for interactive wallet connection/signing. It is not an unattended server treasury signer. The system therefore uses a signer/custody adapter for treasury execution. Trust Wallet can remain the treasury wallet operational interface if a secure approved signing bridge is available; otherwise approval creates a queued execution job and never falsely marks a withdrawal complete.

## Security
Short-lived JWTs, hashed refresh tokens, admin roles, admin 2FA before production withdrawals, strict CORS, rate limiting, audit events, idempotency, DB backups/PITR, monitoring and alerting. Never store a seed phrase/private key in the APK, website, source code or ordinary database.

## Fees
Withdrawal fee policy is server-configured. The requested product target is 1.5%–2.0% by amount band; the live schedule must be explicitly configured and displayed before confirmation.

## Returns
Any weekly percentage shown before a realized server posting is an illustrative projection, not a guaranteed return.

## Operational states
Deposits: pending -> confirming -> completed, or rejected.
Withdrawals: pending -> approved -> processing -> broadcast -> confirming -> completed, or rejected/failed.
Investments: active -> completed/withdrawal_pending -> closed.

## Scale
API instances are stateless. PostgreSQL provides transactional consistency. Workers use leases/locks and idempotency so multiple instances do not double-credit or double-process financial events.

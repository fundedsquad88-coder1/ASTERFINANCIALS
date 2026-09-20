# Aster Financials Backend Foundation

This directory is the production API contract and service boundary for V23 Auto-Invest.

## Principles

- No balances, returns, deposits, withdrawals, referrals or strategy activations are fabricated in the Android client.
- Authentication/session state is server-side.
- The ledger is the source of truth for money.
- Deposit and withdrawal providers are adapters behind explicit interfaces.
- Auto-Invest activation is a server-side transaction, never a localStorage action.
- Admin actions require separate authorization and audit logging.
- HTTPS is mandatory in production.

## Planned services

1. Auth + KYC/AML gateway
2. User/account service
3. Double-entry wallet ledger
4. Deposit adapter (USDT/network/provider)
5. Withdrawal adapter with risk checks and transaction authorization
6. Auto-Invest strategy service
7. Market/news aggregation
8. Referral ledger
9. Notifications
10. Admin/audit service

## API

See `openapi.yaml`. The Android app is intentionally not wired to a fake base URL. Configure the production API origin only after the backend is deployed behind HTTPS.

## Security

Do not put private keys, provider secrets, API signing secrets or database credentials in the APK. Session credentials should use secure server-side session handling; do not place access/refresh tokens in WebView localStorage.

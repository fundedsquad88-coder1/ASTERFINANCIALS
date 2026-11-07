# Aster Financials Backend

Production-oriented service foundation for Aster. This repository contains a runnable FastAPI service with server-side sessions, password hashing, basic user profiles, email verification state, wallet/account records, ledger entries, Auto-Invest state, notifications and referral/account endpoints.

## Run locally

1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL` to PostgreSQL for production; SQLite is only a local development fallback.
3. Install `requirements.txt`.
4. Apply versioned migrations with `alembic upgrade head`.
5. Run `uvicorn app.main:app --reload`.

Docker (run from the `backend/` directory):

`docker compose -f docker-compose.yml up --build`

The compose stack includes a separate blockchain worker. It does not scan TRON unless
`ASTER_TRON_ENABLED=true` is explicitly set. BSC scanning remains disabled until
`ASTER_BSC_RPC_URL` is configured. Keep both disabled in local development unless
you are deliberately testing against a controlled chain environment.

## Security rules

- HTTPS is mandatory outside local development.
- Session credentials are opaque, HttpOnly cookies; passwords are Argon2-hashed.
- Mutating authenticated requests require the Aster CSRF header.
- Provider/API/database secrets never belong in the APK.
- Wallet balances are ledger-backed records; the Android client must never fabricate balances or returns.
- Auto-Invest activation checks authenticated identity and available balance before creating server state.
- Deposits/withdrawals remain provider-gated. The repository contains public treasury receiving-address configuration only; it contains no signing keys or payout credentials.
- Shared treasury deposits are attributed by the member-submitted transaction hash and independently observed transfer event. If a TRON transaction contains multiple USDT transfers to the shared treasury, every matching event is quarantined rather than guessing which member owns it.
- Amount-only matching is prohibited. A unique payment address/reference or an approved gateway allocation mechanism is required before real-money deposits are enabled.
- Identity/KYC verification is intentionally not enabled at the current account stage. Custody/provider adapters, push delivery, admin authorization and audit controls must be connected before handling real customer funds.

## Service boundaries

1. Auth/session
2. User profile + email verification state
3. Wallet + ledger
4. Deposit/withdrawal provider adapters
5. Auto-Invest
6. Market/news aggregation
7. Referral ledger
8. Notifications
9. Admin/audit

The API is deliberately fail-closed where an external financial provider is not configured.


## Deployment gates

This backend is a gateway-independent engineering foundation, not a live-money deployment.
Do not enable mainnet scanning, automatic payouts, or member-facing financial settlement until:
- A payment/custody provider has approved Aster's business model and supplied its integration requirements.
- The deposit allocation model can identify each member's payment unambiguously.
- KYC/AML, operational controls, refund/reversal handling, and jurisdictional compliance have been reviewed.
- Production secrets, HTTPS, backups, monitoring, alerting, and a dedicated VPS/domain are configured.
- Database migrations, integration tests, reconciliation tests, and recovery drills pass against staging infrastructure.

The blockchain worker is a separate process from the API. Deploy it only after its network
configuration and scanner start cursors have been reviewed. The default TRON setting is disabled.

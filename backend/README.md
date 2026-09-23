# Aster Financials Backend

Production-oriented service foundation for Aster. This repository contains a runnable FastAPI service with server-side sessions, password hashing, basic user profiles, email verification state, wallet/account records, ledger entries, Auto-Invest state, notifications and referral/account endpoints.

## Run locally

1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL` to PostgreSQL for production; SQLite is only a local development fallback.
3. Install `requirements.txt`.
4. Run `uvicorn app.main:app --reload`.

Docker:

`docker compose -f docker-compose.yml up --build`

## Security rules

- HTTPS is mandatory outside local development.
- Session credentials are opaque, HttpOnly cookies; passwords are Argon2-hashed.
- Mutating authenticated requests require the Aster CSRF header.
- Provider/API/database secrets never belong in the APK.
- Wallet balances are ledger-backed records; the Android client must never fabricate balances or returns.
- Auto-Invest activation checks authenticated identity and available balance before creating server state.
- Deposits/withdrawals remain provider-gated. No blockchain address or private key is hard-coded.
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

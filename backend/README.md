# Aster Financials Backend

Production-oriented service foundation for Aster. This repository contains a runnable FastAPI service with server-side sessions, password hashing, basic user profiles, email verification state, wallet/account records, ledger entries, Auto-Invest state, notifications and referral/account endpoints.

## Run locally

1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL` to PostgreSQL for production; SQLite is only a local development fallback.
3. Install `requirements.txt`.
4. Export the settings in `.env` into your shell (for example, `set -a && source .env && set +a` on Linux/macOS).
5. Apply versioned migrations with `alembic upgrade head`.
6. Run `uvicorn app.main:app --reload`.

Docker (run from the `backend/` directory):

`docker compose -f docker-compose.yml up --build -d`

Apply migrations inside the API image before using the service:

`docker compose -f docker-compose.yml run --rm api alembic upgrade head`

Then inspect the API at `http://localhost:8000/health` and view logs with
`docker compose -f docker-compose.yml logs -f api worker`.

## Connect the Android app

In the app, open **You → Connect account**, enter the deployed HTTPS API base URL,
and use **Test & save API address** before signing in or creating an account.

For the Android `WebViewAssetLoader` origin, configure the API with:
- `ALLOWED_ORIGINS=https://appassets.androidplatform.net,https://asterfinancials.netlify.app`
- `SESSION_COOKIE_SECURE=true`
- `SESSION_COOKIE_SAMESITE=none`
- `ALLOWED_HOSTS` containing the actual API hostname

The Android WebView accepts third-party cookies, but the API must still issue
`Secure; SameSite=None` cookies over HTTPS for cross-site app-to-API sessions.
For local HTTP development use `SESSION_COOKIE_SECURE=false` and
`SESSION_COOKIE_SAMESITE=lax`; do not use that configuration on an internet-facing deployment.

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
- Auto-Invest activation additionally requires verified KYC and a real execution provider. It returns a fail-closed error until those integrations exist; it does not reserve principal or create a phantom active position.
- Deposits/withdrawals remain provider-gated. The repository contains public treasury receiving-address configuration only; it contains no signing keys or payout credentials.
- A member-submitted transaction hash is a lookup hint, not proof of ownership. Shared-treasury deposits are never automatically credited from a hash claim alone.
- If a transaction contains multiple USDT transfers to the shared treasury, every matching event is quarantined rather than guessing which member owns it.
- A deposit remains quarantined until a unique payment address/reference, an independently verified wallet-ownership/allocation mechanism, or an auditable manual review establishes the member-to-transfer link. Amount-only matching is prohibited.
- Identity/KYC verification is not yet integrated. Deposit intent creation, deposit credit, withdrawal requests/approval, and Auto-Invest activation are blocked for unverified accounts. A KYC provider and reviewed verification workflow must be connected before real customer funds can be accepted.

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

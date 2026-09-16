# Aster Financials — Android + API foundation

Aster Financials is a GitHub-ready Android app plus a TypeScript/Fastify backend foundation.

## Current app

- Native Android Studio/Gradle project
- Aster black/gold UI and reference logo
- Live public BTC/USDT and ETH/USDT market charts via Binance data
- XAU/USDT explicitly marked provider-required; no fake market data
- Account registration/sign-in with bearer session
- Backend-synced USDT wallet balance and activity
- Deposit requests and withdrawal requests
- Trade preview endpoint; no real-money execution
- Earn UI/backend foundation for staking, referrals, and reward history

## Backend

- Fastify API with Helmet and CORS
- PostgreSQL + Prisma persistence
- Password hashing with Node scrypt
- Session tokens stored as hashes in the API process
- Wallet and ledger records designed as the accounting source of truth
- Staking positions and referral relationships persisted in Prisma
- Sandbox staking preview and sandbox stake creation
- Referral code generation and referral relationship tracking
- No blockchain transaction execution or automatic reward settlement yet

## Admin dashboard

The static admin console is at `admin/index.html` and connects to the same API. It provides:

- Admin sign-in using server-side environment credentials
- User, deposit, withdrawal, staking, and ledger views
- Overview metrics
- Manual approval of pending withdrawal requests
- Logout and API-base persistence on the admin device

The admin withdrawal approval currently changes the sandbox database state only. It does **not** broadcast a blockchain transaction or represent a completed customer payout.

## Build the APK on GitHub

1. Open **Actions** in the repository.
2. Select **Build Aster APK**.
3. Run the workflow on `aster-v1`.
4. When green, open the run and download `aster-financials-debug-apk`.
5. The artifact contains `app-debug.apk`.

## Backend CI

The **Backend CI** workflow validates the Prisma schema, generates the Prisma client, and runs the TypeScript build. CI uses a non-production PostgreSQL connection URL and does not connect to a production database.

## Production boundary

This repository is intentionally a sandbox foundation. Real-money trading, binary-options settlement, custody, deposits/withdrawals on-chain, automatic yield/reward settlement, KYC/AML, limits, audit controls, and administrative controls require separate production architecture, security review, market-data/settlement design, and applicable regulatory/licensing work. Do not treat sandbox balances, projected rewards, or trade previews as real customer funds or returns.

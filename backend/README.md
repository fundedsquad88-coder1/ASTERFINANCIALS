# Aster Financials API

Production-oriented backend foundation for authentication and server-side financial records.

## Current endpoints

- GET /health
- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me
- GET /api/account/summary

## Security model

The Android client never decides a user's balance. Balances are derived from server-side ledger entries. Wallet addresses, blockchain verification, investment calculations, withdrawals and referral rewards should be added as backend-controlled modules.

Set DATABASE_URL and JWT_SECRET as deployment secrets. Do not commit real credentials.

## Run locally

npm install
npm start

Blockchain verification:
Run the verification worker separately from the API with npm run worker. It watches configured BEP-20 and TRC-20 treasury addresses, validates USDT transfer records, and uses idempotent transaction identifiers before a submitted deposit can be credited.
Required production configuration is documented in .env.example. The worker must never contain wallet seed phrases or private keys. Treasury signing/execution belongs in a dedicated signer/custody layer.

Withdrawal operations:
Admin endpoints require the authenticated user's email to be listed in ADMIN_EMAILS. Approval calculates the configured fee tier, moves the request to processing, and returns the exact validated destination and net amount. Completion requires the actual outgoing blockchain transaction hash; the API never marks a withdrawal completed merely because an admin clicked approve.
The default fee configuration is 2.00% below 1,000 USDT and 1.50% at/above 1,000 USDT. Change WITHDRAWAL_FEE_TIERS_JSON before production if Aster's commercial fee schedule differs.

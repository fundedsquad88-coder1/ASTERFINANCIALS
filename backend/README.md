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

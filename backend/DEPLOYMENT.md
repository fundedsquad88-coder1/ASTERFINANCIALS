# Aster Financials backend deployment

This repository contains a deployment template for the sandbox backend. The API currently provides account, wallet, staking, referral, admin queue, market-data and trade-preview functionality. It does **not** execute real-money binary trades or submit blockchain transactions.

## Production prerequisites

- A server with Docker Engine and Docker Compose.
- A real PostgreSQL storage volume or managed PostgreSQL service.
- HTTPS termination/reverse proxy in front of the API.
- A domain name for the API.
- Strong production values for `POSTGRES_PASSWORD` and `ADMIN_PASSWORD`.
- A Twelve Data API key configured as `TWELVEDATA_API_KEY` if Gold, Silver, WTI and Brent charts are to be enabled. Twelve Data documents real-time commodity spot data and 1-minute time-series data for commodities including gold, silver and crude oil. citeturn0search0turn1search0
- Secrets stored outside Git; do not commit `.env.production`.
- Appropriate legal/regulatory review before enabling any real-money financial functionality.

## Commodity data

The app keeps the commodity provider key on the backend. The Android client never receives `TWELVEDATA_API_KEY`; it requests Aster's `/api/v1/commodities/:symbol/time-series` endpoint instead. Without the key, the app intentionally shows **PROVIDER REQUIRED** rather than fabricated prices. With the key configured, the API exposes Gold, Silver, WTI and Brent data through the chart screen.

Twelve Data advertises commercial/business use of its commodity data and lists plans starting at $29/month, but the exact plan and redistribution rights should be confirmed with the provider before production launch. citeturn0search0

## Quick deployment with Docker Compose

1. Copy `backend/.env.production.example` to `backend/.env.production` on the server.
2. Replace every placeholder credential with a long random secret and set `TWELVEDATA_API_KEY` to the provider key.
3. From `backend/`, run:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

The API container applies committed Prisma migrations before starting the server. PostgreSQL data is stored in the `aster-postgres-prod` Docker volume.

4. Check the API locally on the server:

```bash
curl http://127.0.0.1:3000/health
```

The health response reports whether the commodity provider is configured, without exposing the API key.

5. Put an HTTPS reverse proxy (for example, Caddy or Nginx) in front of `127.0.0.1:3000`. Do not expose PostgreSQL to the public internet.

## Updating the backend

Pull the desired Git revision and rebuild:

```bash
git pull
docker compose -f backend/docker-compose.prod.yml up -d --build
```

Migrations run automatically during API container startup.

## Secrets and security

Never put production credentials in GitHub source files, Dockerfiles, Android assets, or the APK. Use the deployment host's secret/environment mechanism. Rotate admin credentials if they are ever exposed.

Before real-money use, add a dedicated secret manager, rate limiting, structured audit logs, role-based admin authorization, secure session/token storage, withdrawal approval controls, monitoring/alerts, backups and restore testing, and a proper custody/blockchain integration.

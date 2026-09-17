# Aster Financials backend deployment

This repository contains a sandbox backend foundation and a production deployment template. Real-money binary execution and blockchain transaction submission remain disabled.

## Production baseline

Before exposing the API publicly, provision:

- Managed PostgreSQL or a dedicated PostgreSQL server with automated backups and tested restore procedures.
- A private Docker network and an HTTPS reverse proxy/load balancer in front of the API.
- A DNS name dedicated to the API.
- Production secrets supplied by the hosting provider/secret manager, never committed to Git.
- A Twelve Data API key if commodity charts are enabled; keep the provider key server-side.
- Monitoring for API availability, database health, authentication failures, withdrawal queues and application errors.
- A documented incident-response and credential-rotation procedure.

The existing Compose configuration binds the API to `127.0.0.1:3000` and keeps PostgreSQL on the internal Docker network; PostgreSQL should not be published directly to the Internet.

## Secrets

Copy `backend/.env.production.example` to the deployment host and replace every placeholder. Generate long random values for database and administrator credentials. Do not place production credentials in GitHub source, Dockerfiles, Android assets or the APK.

For an actual deployment, prefer a managed secret store rather than a plaintext `.env.production` file. Rotate credentials immediately if they are exposed.

## Database

The API uses Prisma migrations. Deploy with:

```bash
docker compose -f backend/docker-compose.prod.yml up -d --build
```

The container applies committed migrations before starting the API. Configure automated PostgreSQL backups independently of the application container and periodically perform a restore test.

## HTTPS and proxy

Terminate TLS at a reverse proxy/load balancer and forward only the API traffic to the container. Use HSTS once HTTPS is confirmed working. Do not expose port 5432 publicly.

Restrict CORS to the production website/app origins rather than allowing arbitrary origins when the public deployment is configured.

## Observability

Use the API `/health` endpoint for availability checks. Request IDs are intended to make application logs traceable across a request path. Alert on repeated 5xx responses, database connectivity failures, authentication abuse and unusual financial-queue activity.

## Financial safety boundary

The current API deliberately remains a sandbox. Deposits and withdrawals are records/queues, staking is sandbox functionality, and trade endpoints are previews/records rather than real-money execution. Do not remove that boundary until custody, settlement, accounting, security, compliance and applicable regulatory requirements have been independently reviewed and implemented.

The admin foundation also requires production authorization, MFA, approval workflows and durable audit storage before real-money operations.

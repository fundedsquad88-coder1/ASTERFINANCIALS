# Aster Financials backend — production hardening notes

## Security
- Keep JWT_SECRET, DATABASE_URL, JOB_SECRET and email provider credentials in deployment secrets only.
- Serve the API only over HTTPS in production.
- Restrict CORS to the deployed Aster app/web origins instead of allowing every origin.
- Keep Helmet and the 32 KB JSON request limit enabled.
- Never put private keys, database credentials, or job secrets in the Android APK.

## Database / scale
- Use PostgreSQL with connection pooling and connection limits appropriate to the deployment.
- Keep user-scoped indexes on ledger, deposits, withdrawals, investments and referrals.
- Financial balances remain derived from server-side ledger data; the client never writes balances.
- Weekly investment processing uses row locks plus a unique investment/period constraint to make retries idempotent.

## Operations
- Use /health for load balancer/container health checks.
- Run the weekly accounting endpoints only from a trusted scheduled worker using JOB_SECRET.
- Back up PostgreSQL and test restore procedures before accepting production funds.
- Add centralized error monitoring and audit logs before launch.
- Deploy API and database in separate production environments from development/test data.

## Financial controls
- Deposit records should remain pending until blockchain verification confirms the transaction.
- Withdrawals remain pending until an authorized operational process approves and executes the transfer.
- Never show an unverified deposit as spendable balance.

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

# This revision owns only the foundational account and ledger tables.
# Funding, referrals, auth tokens, email verification, and chain monitoring
# are created by their later versioned migrations.
INITIAL_TABLES = (
    "users",
    "sessions",
    "wallets",
    "idempotency_keys",
    "ledger_entries",
    "ledger_transactions",
    "ledger_postings",
    "autoinvest",
    "valuation_sources",
    "strategy_valuations",
    "notifications",
)


def upgrade():
    from app.main import Base

    tables = [Base.metadata.tables[name] for name in INITIAL_TABLES]
    Base.metadata.create_all(bind=op.get_bind(), tables=tables)


def downgrade():
    from app.main import Base

    tables = [Base.metadata.tables[name] for name in INITIAL_TABLES]
    Base.metadata.drop_all(bind=op.get_bind(), tables=tables)

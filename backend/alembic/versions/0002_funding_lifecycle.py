from alembic import op
import sqlalchemy as sa

revision = "0002_funding_lifecycle"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "deposit_intents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_reference", sa.String(length=160), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("network", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(28, 8), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("deposit_address", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_reference"),
    )
    op.create_index("ix_deposit_intents_user_id", "deposit_intents", ["user_id"])
    op.create_index("ix_deposit_intents_provider_reference", "deposit_intents", ["provider_reference"])
    op.create_index("ix_deposit_intents_status", "deposit_intents", ["status"])

    op.create_table(
        "withdrawal_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_reference", sa.String(length=160), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("network", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=256), nullable=False),
        sa.Column("amount", sa.Numeric(28, 8), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_reference"),
    )
    op.create_index("ix_withdrawal_requests_user_id", "withdrawal_requests", ["user_id"])
    op.create_index("ix_withdrawal_requests_provider_reference", "withdrawal_requests", ["provider_reference"])
    op.create_index("ix_withdrawal_requests_status", "withdrawal_requests", ["status"])

    op.create_table(
        "provider_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("event_id", sa.String(length=200), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_provider_events_event_id", "provider_events", ["event_id"])

def downgrade():
    op.drop_index("ix_provider_events_event_id", table_name="provider_events")
    op.drop_table("provider_events")
    op.drop_index("ix_withdrawal_requests_status", table_name="withdrawal_requests")
    op.drop_index("ix_withdrawal_requests_provider_reference", table_name="withdrawal_requests")
    op.drop_index("ix_withdrawal_requests_user_id", table_name="withdrawal_requests")
    op.drop_table("withdrawal_requests")
    op.drop_index("ix_deposit_intents_status", table_name="deposit_intents")
    op.drop_index("ix_deposit_intents_provider_reference", table_name="deposit_intents")
    op.drop_index("ix_deposit_intents_user_id", table_name="deposit_intents")
    op.drop_table("deposit_intents")

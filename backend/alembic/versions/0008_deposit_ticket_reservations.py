"""Add expiring single-wallet deposit tickets and unique active amounts."""

from alembic import op
import sqlalchemy as sa

revision = "0008_deposit_ticket_reservations"
down_revision = "0007_deposit_tx_claim"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "deposit_intents",
        sa.Column("requested_amount", sa.Numeric(28, 8), nullable=True),
    )
    op.add_column(
        "deposit_intents",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "deposit_intents",
        sa.Column(
            "ticket_mode",
            sa.String(length=40),
            nullable=False,
            server_default="legacy",
        ),
    )
    op.create_index(
        "ix_deposit_intents_expires_at",
        "deposit_intents",
        ["expires_at"],
    )
    # Existing legacy intents are deliberately excluded. New v1 tickets cannot
    # reserve the same amount on the same network while either ticket is active.
    predicate = (
        "ticket_mode = 'single_wallet_ticket_v1' AND status IN "
        "('pending', 'transaction_submitted', 'review_required')"
    )
    op.create_index(
        "uq_deposit_ticket_network_amount_active",
        "deposit_intents",
        ["network", "amount"],
        unique=True,
        postgresql_where=sa.text(predicate),
        sqlite_where=sa.text(predicate),
    )


def downgrade():
    op.drop_index(
        "uq_deposit_ticket_network_amount_active",
        table_name="deposit_intents",
    )
    op.drop_index("ix_deposit_intents_expires_at", table_name="deposit_intents")
    op.drop_column("blockchain_transfers", "chain_timestamp")
    op.drop_column("deposit_intents", "ticket_mode")
    op.drop_column("deposit_intents", "expires_at")
    op.drop_column("deposit_intents", "requested_amount")

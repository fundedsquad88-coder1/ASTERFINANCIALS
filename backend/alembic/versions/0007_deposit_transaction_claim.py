from alembic import op
import sqlalchemy as sa

revision = "0007_deposit_transaction_claim"
down_revision = "0006_blockchain_monitoring"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "deposit_intents",
        sa.Column("tx_hash", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_deposit_intents_tx_hash",
        "deposit_intents",
        ["tx_hash"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_deposit_intents_tx_hash", table_name="deposit_intents")
    op.drop_column("deposit_intents", "tx_hash")

from alembic import op
import sqlalchemy as sa

revision = "0006_blockchain_monitoring"
down_revision = "0005_account_profile"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "blockchain_cursors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("network", sa.String(length=32), nullable=False),
        # TRON cursors are Unix milliseconds, so this must not be a 32-bit INTEGER.
        sa.Column("cursor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("network"),
    )
    op.create_index("ix_blockchain_cursors_network", "blockchain_cursors", ["network"], unique=True)

    op.create_table(
        "blockchain_transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("network", sa.String(length=32), nullable=False),
        sa.Column("tx_hash", sa.String(length=128), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=False),
        sa.Column("token_contract", sa.String(length=128), nullable=False),
        sa.Column("from_address", sa.String(length=256), nullable=False),
        sa.Column("to_address", sa.String(length=256), nullable=False),
        sa.Column("amount", sa.Numeric(28, 8), nullable=False),
        sa.Column("confirmations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("deposit_intent_id", sa.Integer(), sa.ForeignKey("deposit_intents.id"), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("credited_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tx_hash"),
    )
    op.create_index("ix_blockchain_transfers_network", "blockchain_transfers", ["network"])
    op.create_index("ix_blockchain_transfers_tx_hash", "blockchain_transfers", ["tx_hash"], unique=True)
    op.create_index("ix_blockchain_transfers_block_number", "blockchain_transfers", ["block_number"])
    op.create_index("ix_blockchain_transfers_status", "blockchain_transfers", ["status"])
    op.create_index("ix_blockchain_transfers_deposit_intent_id", "blockchain_transfers", ["deposit_intent_id"])

def downgrade():
    op.drop_index("ix_blockchain_transfers_deposit_intent_id", table_name="blockchain_transfers")
    op.drop_index("ix_blockchain_transfers_status", table_name="blockchain_transfers")
    op.drop_index("ix_blockchain_transfers_block_number", table_name="blockchain_transfers")
    op.drop_index("ix_blockchain_transfers_tx_hash", table_name="blockchain_transfers")
    op.drop_index("ix_blockchain_transfers_network", table_name="blockchain_transfers")
    op.drop_table("blockchain_transfers")
    op.drop_index("ix_blockchain_cursors_network", table_name="blockchain_cursors")
    op.drop_table("blockchain_cursors")

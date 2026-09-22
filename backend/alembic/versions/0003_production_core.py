from alembic import op
import sqlalchemy as sa

revision = "0003_production_core"
down_revision = "0002_funding_lifecycle"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("auth_tokens",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("token_hash",sa.String(64),nullable=False),sa.Column("purpose",sa.String(32),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("used_at",sa.DateTime(timezone=True),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("token_hash"))
    op.create_index("ix_auth_tokens_user_id","auth_tokens",["user_id"]); op.create_index("ix_auth_tokens_token_hash","auth_tokens",["token_hash"]); op.create_index("ix_auth_tokens_purpose","auth_tokens",["purpose"]); op.create_index("ix_auth_tokens_expires_at","auth_tokens",["expires_at"])
    op.create_table("referrals",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("referrer_user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("referred_user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("bonus_rate",sa.Numeric(8,4),nullable=False),sa.Column("pending_bonus",sa.Numeric(28,8),nullable=False),sa.Column("paid_bonus",sa.Numeric(28,8),nullable=False),sa.Column("status",sa.String(24),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("referred_user_id"))
    op.create_index("ix_referrals_referrer_user_id","referrals",["referrer_user_id"]); op.create_index("ix_referrals_referred_user_id","referrals",["referred_user_id"])
    op.create_table("audit_events",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=True),sa.Column("event_type",sa.String(80),nullable=False),sa.Column("metadata_json",sa.String(4000),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_audit_events_user_id","audit_events",["user_id"]); op.create_index("ix_audit_events_event_type","audit_events",["event_type"])

def downgrade():
    op.drop_index("ix_audit_events_event_type",table_name="audit_events"); op.drop_index("ix_audit_events_user_id",table_name="audit_events"); op.drop_table("audit_events")
    op.drop_index("ix_referrals_referred_user_id",table_name="referrals"); op.drop_index("ix_referrals_referrer_user_id",table_name="referrals"); op.drop_table("referrals")
    op.drop_index("ix_auth_tokens_expires_at",table_name="auth_tokens"); op.drop_index("ix_auth_tokens_purpose",table_name="auth_tokens"); op.drop_index("ix_auth_tokens_token_hash",table_name="auth_tokens"); op.drop_index("ix_auth_tokens_user_id",table_name="auth_tokens"); op.drop_table("auth_tokens")

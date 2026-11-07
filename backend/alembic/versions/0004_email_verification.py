from alembic import op
import sqlalchemy as sa
revision="0004_email_verification"
down_revision="0003_production_core"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("email_verifications",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),sa.Column("token_hash",sa.String(64),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("verified_at",sa.DateTime(timezone=True),nullable=True),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("token_hash"))
    op.create_index("ix_email_verifications_user_id","email_verifications",["user_id"]); op.create_index("ix_email_verifications_token_hash","email_verifications",["token_hash"]); op.create_index("ix_email_verifications_expires_at","email_verifications",["expires_at"])

def downgrade():
    op.drop_index("ix_email_verifications_expires_at",table_name="email_verifications"); op.drop_index("ix_email_verifications_token_hash",table_name="email_verifications"); op.drop_index("ix_email_verifications_user_id",table_name="email_verifications"); op.drop_table("email_verifications")

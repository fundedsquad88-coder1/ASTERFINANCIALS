from alembic import op
import sqlalchemy as sa

revision = "0005_account_profile"
down_revision = "0004_email_verification"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("country", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.alter_column("users", "email_verified", server_default=None)

def downgrade():
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "country")
    op.drop_column("users", "phone")
    op.drop_column("users", "first_name")
    op.drop_column("users", "username")

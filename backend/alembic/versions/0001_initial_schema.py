from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Initial schema is created by SQLAlchemy metadata during local bootstrap.
    # This revision establishes a stable migration baseline; future schema changes must be additive migrations.
    pass

def downgrade():
    pass

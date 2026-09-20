from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    from app.main import Base
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    from app.main import Base
    Base.metadata.drop_all(bind=op.get_bind())

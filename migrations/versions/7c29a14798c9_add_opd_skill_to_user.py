"""add opd_skill to user"""

revision = '7c29a14798c9'
down_revision = '36e28fa7db45'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('opd_skill', sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('opd_skill')

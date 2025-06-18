"""add languages column to user"""

revision = 'f1f2f3f4f5f6'
down_revision = '58db3b0d3a96'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('languages', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('languages')

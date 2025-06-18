"""add elo_sigma to user model"""

revision = '58db3b0d3a96'
down_revision = 'abcdef123456'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('elo_sigma', sa.Float(), nullable=True, server_default='333.3333333333333'))
    op.execute("UPDATE user SET elo_sigma = 333.3333333333333")
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('elo_sigma', server_default=None)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('elo_sigma')


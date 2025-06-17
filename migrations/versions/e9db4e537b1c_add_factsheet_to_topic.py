"""add factsheet column to topic"""

revision = 'e9db4e537b1c'
down_revision = '363076fe0622'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    with op.batch_alter_table('topic', schema=None) as batch_op:
        batch_op.add_column(sa.Column('factsheet', sa.Text(), nullable=True))

def downgrade():
    with op.batch_alter_table('topic', schema=None) as batch_op:
        batch_op.drop_column('factsheet')

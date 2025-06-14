"""remove first_name unique"""

revision = '363076fe0622'
down_revision = '1c4cfe455b23'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_constraint('user_username_key', type_='unique')


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.create_unique_constraint('user_username_key', ['first_name'])

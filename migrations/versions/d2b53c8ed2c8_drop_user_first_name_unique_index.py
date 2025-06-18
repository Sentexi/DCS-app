"""drop leftover unique index on user.first_name"""

revision = 'd2b53c8ed2c8'
down_revision = 'f1f2f3f4f5f6'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        op.execute('DROP INDEX IF EXISTS sqlite_autoindex_user_2')
    else:
        # Attempt to drop by common constraint/index name if it exists
        op.execute('DROP INDEX IF EXISTS user_username_key')


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.create_unique_constraint('user_username_key', ['first_name'])

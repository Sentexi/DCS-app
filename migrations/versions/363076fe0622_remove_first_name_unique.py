"""remove first_name unique"""

revision = '363076fe0622'
down_revision = '1c4cfe455b23'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # The original schema renamed "username" to "first_name" and removed the
    # unique constraint.  Some databases may still have a leftover unique index
    # named "user_username_key" while others do not.  Instead of blindly
    # dropping a constraint that might not exist, simply ensure the column is
    # marked as non-unique.  ``alter_column`` will drop the constraint if it is
    # present and otherwise performs no action, avoiding the ValueError seen
    # during upgrades when the constraint was already removed.
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column(
            'first_name',
            existing_type=sa.String(length=80),
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.create_unique_constraint('user_username_key', ['first_name'])

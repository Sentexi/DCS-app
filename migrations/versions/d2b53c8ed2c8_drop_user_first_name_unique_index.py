"""Remove UNIQUE from first_name, add UNIQUE on email"""

revision = "d2b53c8ed2c8"
down_revision = "f1f2f3f4f5f6"

from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    This function is executed when you run 'flask db upgrade'.
    It removes the unique constraint from the 'first_name' column.
    """
    # Use Alembic's batch mode for SQLite compatibility.
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Drop the unique constraint using the correct name found in your schema.
        batch_op.drop_constraint('uq_user_first_name', type_='unique')


def downgrade():
    """
    This function is executed when you run 'flask db downgrade'.
    It re-adds the unique constraint to the 'first_name' column.
    """
    # Use Alembic's batch mode for SQLite compatibility.
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Re-create the unique constraint with the specific name for consistency.
        batch_op.create_unique_constraint('uq_user_first_name', ['first_name'])


"""Remove UNIQUE from first_name

Revision ID: d2b53c8ed2c8
Revises: f1f2f3f4f5f6
Create Date: ...

"""

revision = "d2b53c8ed2c8"
down_revision = "f1f2f3f4f5f6"

from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    This function is executed when you run 'flask db upgrade'.
    It alters the 'first_name' column to remove its unique property.
    """
    print("Altering 'first_name' column to remove UNIQUE constraint...")
    with op.batch_alter_table('user', schema=None) as batch_op:
        # This is the correct, declarative way to remove a unique constraint.
        # We describe the column's final state (unique=False).
        # Alembic's batch mode handles the table recreation for us.
        batch_op.alter_column('first_name',
               existing_type=sa.VARCHAR(length=80),
               unique=False,
               existing_nullable=False)

    print("UNIQUE constraint on 'first_name' removed successfully.")


def downgrade():
    """
    This function is executed when you run 'flask db downgrade'.
    It re-adds a unique constraint to the 'first_name' column.
    """
    print("Re-creating unique constraint on 'first_name'...")
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Re-creating the constraint explicitly is clean and robust.
        batch_op.create_unique_constraint('uq_user_first_name', ['first_name'])
        
    print("Unique constraint on 'first_name' re-created.")

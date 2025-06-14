"""add first and last name fields

Revision ID: 1a2b3c4d5e6f
Revises: 0d2e6c501f2d
Create Date: 2025-05-28 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = '0d2e6c501f2d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column(
            'username',
            new_column_name='first_name',
            existing_type=sa.String(length=80),
            existing_nullable=False,
            existing_server_default=None,
            unique=False
        )
        batch_op.add_column(sa.Column('last_name', sa.String(length=80), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('last_name')
        batch_op.alter_column(
            'first_name',
            new_column_name='username',
            existing_type=sa.String(length=80),
            existing_nullable=False,
            existing_server_default=None,
            unique=True
        )

"""add assignment_mode column to debate

Revision ID: c05d7f1446ab
Revises: 363076fe0622
Create Date: 2025-07-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c05d7f1446ab'
down_revision = 'e9db4e537b1c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('debate', schema=None) as batch_op:
        batch_op.add_column(sa.Column('assignment_mode', sa.Enum('True random', 'Random', 'Skill based', 'ProAm', name='assignment_mode'), nullable=True))


def downgrade():
    with op.batch_alter_table('debate', schema=None) as batch_op:
        batch_op.drop_column('assignment_mode')

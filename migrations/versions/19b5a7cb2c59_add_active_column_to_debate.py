"""add active column to debate

Revision ID: 19b5a7cb2c59
Revises: 0d2e6c501f2d
Create Date: 2025-06-13 10:53:04.065910

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19b5a7cb2c59'
down_revision = '0d2e6c501f2d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('debate', schema=None) as batch_op:
        batch_op.add_column(sa.Column('active', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('debate', schema=None) as batch_op:
        batch_op.drop_column('active')

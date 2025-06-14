"""add pending_user table"""

revision = '1c4cfe455b23'
down_revision = '7c29a14798c9'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'pending_user',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('first_name', sa.String(length=80), nullable=False),
        sa.Column('last_name', sa.String(length=80), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password', sa.String(length=256), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('email')
    )


def downgrade():
    op.drop_table('pending_user')

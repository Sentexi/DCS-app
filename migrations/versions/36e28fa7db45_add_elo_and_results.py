"""add elo rating and result tables

Revision ID: 36e28fa7db45
Revises: 1a2b3c4d5e6f
Create Date: 2025-05-30 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '36e28fa7db45'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('elo_rating', sa.Integer(), server_default='1000', nullable=True))
    op.create_table(
        'opd_result',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('debate_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('points', sa.Float()),
        sa.ForeignKeyConstraint(['debate_id'], ['debate.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.UniqueConstraint('debate_id', 'user_id', name='opd_result_unique')
    )
    op.create_table(
        'elo_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('debate_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('old_elo', sa.Float(), nullable=False),
        sa.Column('new_elo', sa.Float(), nullable=False),
        sa.Column('change', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['debate_id'], ['debate.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.UniqueConstraint('debate_id', 'user_id', name='elo_log_unique')
    )
    op.execute("UPDATE user SET elo_rating = 1000")
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('elo_rating', server_default=None)


def downgrade():
    op.drop_table('elo_log')
    op.drop_table('opd_result')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('elo_rating')

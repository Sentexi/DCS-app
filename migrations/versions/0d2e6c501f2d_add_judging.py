"""add judging models"""

revision = '0d2e6c501f2d'
down_revision = 'ee128683fcd2'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'score',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('debate_id', sa.Integer(), nullable=False),
        sa.Column('speaker_id', sa.Integer(), nullable=False),
        sa.Column('judge_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['debate_id'], ['debate.id']),
        sa.ForeignKeyConstraint(['speaker_id'], ['user.id']),
        sa.ForeignKeyConstraint(['judge_id'], ['user.id']),
        sa.UniqueConstraint('debate_id', 'speaker_id', 'judge_id', name='score_unique')
    )
    op.create_table(
        'bp_rank',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('debate_id', sa.Integer(), nullable=False),
        sa.Column('team', sa.String(length=8), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['debate_id'], ['debate.id']),
        sa.UniqueConstraint('debate_id', 'team', name='bp_rank_unique')
    )

def downgrade():
    op.drop_table('bp_rank')
    op.drop_table('score')

"""add second voting support"""

revision = 'abcdef123456'
down_revision = 'c05d7f1446ab'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('debate', schema=None) as batch_op:
        batch_op.add_column(sa.Column('second_voting_open', sa.Boolean(), nullable=True, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('second_voting_topics', sa.String(), nullable=True))
    with op.batch_alter_table('vote', schema=None) as batch_op:
        batch_op.add_column(sa.Column('round', sa.Integer(), nullable=True, server_default='1'))
        batch_op.drop_constraint('_user_topic_uc', type_='unique')
        batch_op.create_unique_constraint('_user_topic_round_uc', ['user_id', 'topic_id', 'round'])


def downgrade():
    with op.batch_alter_table('vote', schema=None) as batch_op:
        batch_op.drop_constraint('_user_topic_round_uc', type_='unique')
        batch_op.create_unique_constraint('_user_topic_uc', ['user_id', 'topic_id'])
        batch_op.drop_column('round')
    with op.batch_alter_table('debate', schema=None) as batch_op:
        batch_op.drop_column('second_voting_topics')
        batch_op.drop_column('second_voting_open')

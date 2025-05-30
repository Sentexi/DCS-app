"""Add user profile and skill columns

Revision ID: b47584362314
Revises: 45a0e1ecbe40
Create Date: 2025-05-24 22:51:58.149142

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b47584362314'
down_revision = '45a0e1ecbe40'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date_joined_choice', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('judge_choice', sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column('debate_skill', sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column('judge_skill', sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column('debate_count', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('debate_count')
        batch_op.drop_column('judge_skill')
        batch_op.drop_column('debate_skill')
        batch_op.drop_column('judge_choice')
        batch_op.drop_column('date_joined_choice')

    # ### end Alembic commands ###

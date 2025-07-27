"""Remove UNIQUE from first_name, add UNIQUE on email"""

revision = "d2b53c8ed2c8"
down_revision = "f1f2f3f4f5f6"

from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    Rebuilds the user table to ensure 'first_name' is not unique
    and 'email' is unique. This is the definitive "catch-all" method.
    """
    print("Rebuilding user table to apply new constraint rules...")

    # Define the exact final schema for the user table.
    # YOU MUST LIST ALL COLUMNS FROM YOUR USER MODEL HERE.
    final_user_table = sa.Table(
        "user",
        sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        # 'first_name' is NOT unique in the final schema.
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=True),
        # 'email' IS unique in the final schema.
        sa.Column("email", sa.String(120), unique=True, nullable=False),
        sa.Column("password", sa.String(256), nullable=False),
        sa.Column("is_admin", sa.Boolean),
        sa.Column("date_joined_choice", sa.String(16)),
        sa.Column("judge_choice", sa.String(8)),
        sa.Column("languages", sa.String(64)),
        sa.Column("debate_skill", sa.String(24)),
        sa.Column("judge_skill", sa.String(16)),
        sa.Column("debate_count", sa.Integer),
        sa.Column("last_seen", sa.DateTime),
        sa.Column("elo_rating", sa.Integer),
        sa.Column("elo_sigma", sa.Float),
        sa.Column("opd_skill", sa.Float),
    )

    # Rebuild the table using the blueprint defined above.
    with op.batch_alter_table(
        "user",
        copy_from=final_user_table,
        recreate="always"  # This forces the rebuild
    ) as batch_op:
        # No operations are needed inside the block because the
        # schema is entirely defined by the `copy_from` argument.
        pass

    print("User table rebuild complete.")


def downgrade():
    """Reverts the changes from the upgrade by rebuilding the table again."""
    print("Rebuilding user table to revert constraint changes...")

    # Define the schema as it was BEFORE this migration.
    original_user_table = sa.Table(
        "user",
        sa.MetaData(),
        sa.Column("id", sa.Integer, primary_key=True),
        # 'first_name' is unique again in the original schema.
        sa.Column("first_name", sa.String(80), unique=True, nullable=False),
        sa.Column("last_name", sa.String(80), nullable=True),
        # 'email' is NOT unique in the original schema.
        sa.Column("email", sa.String(120), nullable=False),
        sa.Column("password", sa.String(256), nullable=False),
        # YOU MUST LIST ALL YOUR OTHER COLUMNS HERE AS WELL.
        sa.Column("is_admin", sa.Boolean),
        sa.Column("date_joined_choice", sa.String(16)),
        sa.Column("judge_choice", sa.String(8)),
        sa.Column("languages", sa.String(64)),
        sa.Column("debate_skill", sa.String(24)),
        sa.Column("judge_skill", sa.String(16)),
        sa.Column("debate_count", sa.Integer),
        sa.Column("last_seen", sa.DateTime),
        sa.Column("elo_rating", sa.Integer),
        sa.Column("elo_sigma", sa.Float),
        sa.Column("opd_skill", sa.Float),
    )

    with op.batch_alter_table(
        "user",
        copy_from=original_user_table,
        recreate="always"
    ) as batch_op:
        pass

    print("Downgrade rebuild complete.")

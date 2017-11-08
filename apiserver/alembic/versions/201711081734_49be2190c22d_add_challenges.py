"""Add challenges

Revision ID: 49be2190c22d
Revises: 33de9025cc63
Create Date: 2017-11-08 17:34:20.134831+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '49be2190c22d'
down_revision = '33de9025cc63'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "challenge",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created", sa.DateTime,
                  nullable=False,
                  server_default=sa.sql.func.now()),
        sa.Column("finished", sa.DateTime,
                  nullable=True),
        sa.Column("winner",
                  mysql.MEDIUMINT(display_width=8, unsigned=True),
                  sa.ForeignKey("user.id"),
                  nullable=True),
    )

    op.create_table(
        "user_challenge",
        sa.Column("challenge_id",
                  sa.Integer,
                  sa.ForeignKey("challenge.id"),
                  primary_key=True),
        sa.Column("user_id",
                  mysql.MEDIUMINT(display_width=8, unsigned=True),
                  sa.ForeignKey("user.id"),
                  primary_key=True),
    )

    op.add_column(
        "game",
        sa.Column("challenge_id",
                  sa.Integer,
                  sa.ForeignKey("challenge.id"),
                  nullable=True)
    )


def downgrade():
    pass

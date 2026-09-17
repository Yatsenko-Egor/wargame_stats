"""add player role

Revision ID: d864634c074f
Revises: 99e8c9d0b454
Create Date: 2026-09-16 11:49:42.883955

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d864634c074f"
down_revision = "99e8c9d0b454"
branch_labels = None
depends_on = None


player_role = sa.Enum(
    "USER",
    "MODERATOR",
    "ADMIN",
    name="player_role",
)


def upgrade():
    player_role.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "player",
        sa.Column(
            "role",
            player_role,
            server_default="USER",
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("player", "role")

    player_role.drop(
        op.get_bind(),
        checkfirst=True,
    )
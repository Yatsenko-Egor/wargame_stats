"""add WAIT to confirmation_response

Revision ID: <id>
Revises: 6288bcac8b5b_add_wait_to_confirmation_response.py
Create Date: ...

"""
from alembic import op


revision = '<id>'
down_revision = '97bbd90e4be6'
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE confirmation_response ADD VALUE 'WAIT'"
        )


def downgrade():
    pass
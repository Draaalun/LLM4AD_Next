"""add is_contact to live_code

Revision ID: b2d3f4a5c6e7
Revises: a1c2e3f4b5d6
Create Date: 2026-06-04 13:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b2d3f4a5c6e7'
down_revision = 'a1c2e3f4b5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'live_code',
        sa.Column(
            'is_contact',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        op.f('ix_live_code_is_contact'),
        'live_code',
        ['is_contact'],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f('ix_live_code_is_contact'), table_name='live_code')
    op.drop_column('live_code', 'is_contact')

"""add generation_kind column to chat_tune_message

Revision ID: b9c0d1e2f3a4
Revises: 29d4d9705225
Create Date: 2026-05-30 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b9c0d1e2f3a4'
down_revision = '29d4d9705225'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'chat_tune_message',
        sa.Column('generation_kind', sa.String(length=20), nullable=True),
    )


def downgrade():
    op.drop_column('chat_tune_message', 'generation_kind')

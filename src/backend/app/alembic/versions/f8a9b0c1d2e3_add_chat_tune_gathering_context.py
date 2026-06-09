"""add gathering_context column to chat_tune_session

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-05-27 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f8a9b0c1d2e3'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'chat_tune_session',
        sa.Column('gathering_context', sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_column('chat_tune_session', 'gathering_context')

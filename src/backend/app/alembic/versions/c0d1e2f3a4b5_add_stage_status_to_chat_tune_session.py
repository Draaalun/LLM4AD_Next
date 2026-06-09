"""add stage status columns to chat_tune_session

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-05-30 11:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c0d1e2f3a4b5'
down_revision = 'b9c0d1e2f3a4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'chat_tune_session',
        sa.Column(
            'gathering_status',
            sa.String(length=20),
            nullable=False,
            server_default='not_started',
        ),
    )
    op.add_column(
        'chat_tune_session',
        sa.Column(
            'build_status',
            sa.String(length=20),
            nullable=False,
            server_default='not_started',
        ),
    )
    op.add_column(
        'chat_tune_session',
        sa.Column(
            'review_status',
            sa.String(length=20),
            nullable=False,
            server_default='not_started',
        ),
    )
    op.add_column(
        'chat_tune_session',
        sa.Column(
            'active_stage',
            sa.String(length=20),
            nullable=False,
            server_default='gathering',
        ),
    )


def downgrade():
    op.drop_column('chat_tune_session', 'active_stage')
    op.drop_column('chat_tune_session', 'review_status')
    op.drop_column('chat_tune_session', 'build_status')
    op.drop_column('chat_tune_session', 'gathering_status')

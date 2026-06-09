"""add feedback table

Revision ID: a238b3b3388e46ae
Revises: 43a838dff679
Create Date: 2026-05-03 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a238b3b3388e46ae'
down_revision = '43a838dff679'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'feedback',
        sa.Column('created_time', sa.DateTime(), nullable=False),
        sa.Column('updated_time', sa.DateTime(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('browser_info', sa.String(length=512), nullable=True),
        sa.Column('page_url', sa.String(length=1024), nullable=True),
        sa.Column('screenshot_url', sa.String(length=1024), nullable=True),
        sa.Column('attachments', sa.Text(), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=False),
        sa.Column('admin_reply', sa.Text(), nullable=True),
        sa.Column('admin_id', sa.Uuid(), nullable=True),
        sa.Column('resolved_time', sa.DateTime(), nullable=True),
        sa.Column('tags', sa.String(length=512), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['admin_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_feedback_user_id'),
        'feedback',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_feedback_status'),
        'feedback',
        ['status'],
        unique=False,
    )
    op.create_index(
        op.f('ix_feedback_type'),
        'feedback',
        ['type'],
        unique=False,
    )
    op.create_index(
        op.f('ix_feedback_created_time'),
        'feedback',
        ['created_time'],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f('ix_feedback_created_time'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_type'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_status'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_user_id'), table_name='feedback')
    op.drop_table('feedback')

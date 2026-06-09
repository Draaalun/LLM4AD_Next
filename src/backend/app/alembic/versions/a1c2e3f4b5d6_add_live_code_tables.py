"""add live code tables

Revision ID: a1c2e3f4b5d6
Revises: f1a2b3c4d5e6
Create Date: 2026-06-04 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a1c2e3f4b5d6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'live_code',
        sa.Column('created_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('strategy', sa.String(length=32), nullable=False),
        sa.Column('landing_title', sa.String(length=255), nullable=True),
        sa.Column('landing_tip', sa.String(length=512), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('slug', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('rotation_cursor', sa.Integer(), nullable=False),
        sa.Column('total_scans', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_live_code_slug'), 'live_code', ['slug'], unique=True)
    op.create_index(op.f('ix_live_code_user_id'), 'live_code', ['user_id'], unique=False)
    op.create_index('ix_live_code_created_time', 'live_code', ['created_time'], unique=False)

    op.create_table(
        'live_code_target',
        sa.Column('created_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scan_limit', sa.Integer(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('live_code_id', sa.Uuid(), nullable=False),
        sa.Column('image_key', sa.String(length=1024), nullable=False),
        sa.Column('content_type', sa.String(length=128), nullable=False),
        sa.Column('original_filename', sa.String(length=512), nullable=True),
        sa.Column('scan_count', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['live_code_id'], ['live_code.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_live_code_target_live_code_id',
        'live_code_target',
        ['live_code_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_live_code_target_live_code_id', table_name='live_code_target')
    op.drop_table('live_code_target')
    op.drop_index('ix_live_code_created_time', table_name='live_code')
    op.drop_index(op.f('ix_live_code_user_id'), table_name='live_code')
    op.drop_index(op.f('ix_live_code_slug'), table_name='live_code')
    op.drop_table('live_code')

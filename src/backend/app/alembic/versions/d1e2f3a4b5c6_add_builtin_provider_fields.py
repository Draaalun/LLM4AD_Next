"""add builtin provider fields to llmprovider

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-01 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c0d1e2f3a4b5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'llmprovider',
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'llmprovider',
        sa.Column('visible_to_all', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('llmprovider', 'user_id', existing_type=sa.Uuid(), nullable=True)
    # 仅对内置行强制 name 唯一；用户行允许重名
    op.create_index(
        'uq_provider_builtin_name',
        'llmprovider',
        ['name'],
        unique=True,
        postgresql_where=sa.text('is_builtin = true'),
    )


def downgrade():
    op.drop_index('uq_provider_builtin_name', table_name='llmprovider')
    op.alter_column('llmprovider', 'user_id', existing_type=sa.Uuid(), nullable=False)
    op.drop_column('llmprovider', 'visible_to_all')
    op.drop_column('llmprovider', 'is_builtin')

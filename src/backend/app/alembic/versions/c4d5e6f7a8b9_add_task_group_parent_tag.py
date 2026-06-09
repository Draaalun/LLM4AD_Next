"""add task group_id, parent_id, tag columns

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('task', sa.Column('group_id', sa.Uuid(), nullable=True))
    op.add_column('task', sa.Column('parent_id', sa.Uuid(), nullable=True))
    op.add_column('task', sa.Column('tag', sa.String(length=255), nullable=True))
    op.create_index('ix_task_group_id', 'task', ['group_id'])
    op.create_index('ix_task_parent_id', 'task', ['parent_id'])


def downgrade():
    op.drop_index('ix_task_parent_id', table_name='task')
    op.drop_index('ix_task_group_id', table_name='task')
    op.drop_column('task', 'tag')
    op.drop_column('task', 'parent_id')
    op.drop_column('task', 'group_id')

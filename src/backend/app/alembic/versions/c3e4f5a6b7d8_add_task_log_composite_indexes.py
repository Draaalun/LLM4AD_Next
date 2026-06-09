"""add composite indexes to task_log for fast filtered log queries

Revision ID: c3e4f5a6b7d8
Revises: b2d3f4a5c6e7
Create Date: 2026-06-04 14:30:00.000000

Adds two composite indexes to ``task_log`` so the log-list API can serve
``WHERE task_id=? AND type=? ORDER BY timestamp, id`` (and the all-types,
time-ordered cursor pagination) via an index range scan instead of fetching
every row of the task and filtering/sorting in memory.

Note: on a very large existing ``task_log`` table, a plain ``CREATE INDEX``
takes a write lock for the duration of the build. If that is a concern, build
them manually with ``CREATE INDEX CONCURRENTLY`` (outside a transaction) instead
of running this migration during peak hours.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c3e4f5a6b7d8'
down_revision = 'b2d3f4a5c6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'ix_task_log_task_type_ts',
        'task_log',
        ['task_id', 'type', 'timestamp', 'id'],
        unique=False,
    )
    op.create_index(
        'ix_task_log_task_ts',
        'task_log',
        ['task_id', 'timestamp', 'id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_task_log_task_ts', table_name='task_log')
    op.drop_index('ix_task_log_task_type_ts', table_name='task_log')

"""Make task project_id not nullable

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-05-23 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd6e7f8a9b0c1'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade():
    # Drop orphan tasks (project_id IS NULL) before enforcing NOT NULL. These are
    # unreachable leftovers from the brief nullable window; child rows cascade-delete.
    op.execute("DELETE FROM task WHERE project_id IS NULL")
    op.alter_column('task', 'project_id', existing_type=sa.Uuid(), nullable=False)


def downgrade():
    op.alter_column('task', 'project_id', existing_type=sa.Uuid(), nullable=True)

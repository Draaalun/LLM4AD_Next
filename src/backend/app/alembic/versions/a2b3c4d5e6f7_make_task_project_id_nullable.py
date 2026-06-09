"""Make task project_id nullable

Revision ID: a2b3c4d5e6f7
Revises: b82a9f66ee94
Create Date: 2026-05-19 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = 'b82a9f66ee94'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('task', 'project_id', existing_type=sa.Uuid(), nullable=True)


def downgrade():
    op.alter_column('task', 'project_id', existing_type=sa.Uuid(), nullable=False)

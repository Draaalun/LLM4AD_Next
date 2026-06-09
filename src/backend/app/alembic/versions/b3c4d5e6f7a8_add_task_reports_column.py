"""add task reports column

Revision ID: b3c4d5e6f7a8
Revises: ef5f353e97a8
Create Date: 2026-04-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'ef5f353e97a8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('task', sa.Column('reports', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('task', 'reports')

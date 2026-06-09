"""add task logs column

Revision ID: a1b2c3d4e5f6
Revises: 6b48e96cedac
Create Date: 2026-04-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6b48e96cedac'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('task', sa.Column('logs', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('task', 'logs')

"""add_task_result_render_column

Revision ID: b82a9f66ee94
Revises: 5cc02a01d450
Create Date: 2026-05-13 11:10:08.613579

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'b82a9f66ee94'
down_revision = '5cc02a01d450'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('task', sa.Column('result_render', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('task', 'result_render')

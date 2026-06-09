"""user_default_model provider fkeys ON DELETE SET NULL

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-01 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a8b9c0d1e2f3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


_PROVIDER_COLUMNS = (
    'planner_provider_id',
    'coder_provider_id',
    'report_provider_id',
    'other_provider_id',
)


def upgrade():
    for column in _PROVIDER_COLUMNS:
        constraint_name = f'user_default_model_{column}_fkey'
        op.drop_constraint(constraint_name, 'user_default_model', type_='foreignkey')
        op.create_foreign_key(
            constraint_name,
            'user_default_model',
            'llmprovider',
            [column],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    for column in _PROVIDER_COLUMNS:
        constraint_name = f'user_default_model_{column}_fkey'
        op.drop_constraint(constraint_name, 'user_default_model', type_='foreignkey')
        op.create_foreign_key(
            constraint_name,
            'user_default_model',
            'llmprovider',
            [column],
            ['id'],
        )

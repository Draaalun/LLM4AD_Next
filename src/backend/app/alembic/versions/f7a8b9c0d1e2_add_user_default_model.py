"""add user_default_model table

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-29 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f7a8b9c0d1e2'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_default_model',
        sa.Column('created_time', sa.DateTime(), nullable=False),
        sa.Column('updated_time', sa.DateTime(), nullable=False),
        sa.Column('planner_provider_id', sa.Uuid(), nullable=True),
        sa.Column('planner_model_name', sa.String(length=255), nullable=True),
        sa.Column('coder_provider_id', sa.Uuid(), nullable=True),
        sa.Column('coder_model_name', sa.String(length=255), nullable=True),
        sa.Column('report_provider_id', sa.Uuid(), nullable=True),
        sa.Column('report_model_name', sa.String(length=255), nullable=True),
        sa.Column('other_provider_id', sa.Uuid(), nullable=True),
        sa.Column('other_model_name', sa.String(length=255), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['planner_provider_id'], ['llmprovider.id']),
        sa.ForeignKeyConstraint(['coder_provider_id'], ['llmprovider.id']),
        sa.ForeignKeyConstraint(['report_provider_id'], ['llmprovider.id']),
        sa.ForeignKeyConstraint(['other_provider_id'], ['llmprovider.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_user_default_model_user_id'),
        'user_default_model',
        ['user_id'],
        unique=True,
    )

    # Seed a default model config record for every existing user
    op.execute(
        """
        INSERT INTO user_default_model (id, user_id, created_time, updated_time)
        SELECT gen_random_uuid(), id, NOW(), NOW()
        FROM "user"
        """
    )


def downgrade():
    op.drop_index(op.f('ix_user_default_model_user_id'), table_name='user_default_model')
    op.drop_table('user_default_model')

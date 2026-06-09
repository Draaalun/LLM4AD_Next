"""add email_verified column to user table

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-25 20:30:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    # Mark all existing users as verified
    op.execute("UPDATE \"user\" SET email_verified = true")


def downgrade():
    op.drop_column('user', 'email_verified')

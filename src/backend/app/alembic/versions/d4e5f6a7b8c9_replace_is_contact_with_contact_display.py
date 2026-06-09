"""replace is_contact with contact_display on live_code

Revision ID: d4e5f6a7b8c9
Revises: c3e4f5a6b7d8
Create Date: 2026-06-05 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3e4f5a6b7d8'
branch_labels = None
depends_on = None


def upgrade():
    # 新增 contact_display 列（默认 NONE）。
    # 注意：本项目约定枚举列按成员「名」存储（与 strategy 的 SEQUENTIAL 等一致），
    # SQLAlchemy 的 Enum 类型读写均使用 Enum.name，故此处统一用大写名。
    op.add_column(
        'live_code',
        sa.Column(
            'contact_display',
            sa.String(length=16),
            nullable=False,
            server_default='NONE',
        ),
    )
    # 旧的联系活码迁移为「展示永久码」模式，保持现有行为不变
    op.execute(
        "UPDATE live_code SET contact_display = 'LANDING' WHERE is_contact = true"
    )
    op.create_index(
        op.f('ix_live_code_contact_display'),
        'live_code',
        ['contact_display'],
        unique=False,
    )
    # 移除旧的布尔字段
    op.drop_index(op.f('ix_live_code_is_contact'), table_name='live_code')
    op.drop_column('live_code', 'is_contact')


def downgrade():
    op.add_column(
        'live_code',
        sa.Column(
            'is_contact',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        "UPDATE live_code SET is_contact = true WHERE contact_display <> 'NONE'"
    )
    op.create_index(
        op.f('ix_live_code_is_contact'),
        'live_code',
        ['is_contact'],
        unique=False,
    )
    op.drop_index(op.f('ix_live_code_contact_display'), table_name='live_code')
    op.drop_column('live_code', 'contact_display')

"""encrypt llmprovider credential columns

Revision ID: f1a2b3c4d5e6
Revises: d1e2f3a4b5c6
Create Date: 2026-06-02 10:00:00.000000

将 llmprovider 的 api_key / auth_token 由明文 VARCHAR(512) 改为 Text，
并加密回填存量明文数据。解密侧对历史明文向后兼容，故回填失败不影响读取。
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.sql import column, table

from app.core.encryption import encrypt_secret

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None

# 轻量表引用，仅用于数据回填
_llmprovider = table(
    'llmprovider',
    column('id', sa.Uuid()),
    column('api_key', sa.String()),
    column('auth_token', sa.String()),
)


def upgrade():
    # 1) 放宽列类型：密文长于明文，改用 Text
    op.alter_column(
        'llmprovider', 'api_key',
        existing_type=sa.String(length=512), type_=Text(), existing_nullable=False,
    )
    op.alter_column(
        'llmprovider', 'auth_token',
        existing_type=sa.String(length=512), type_=Text(), existing_nullable=False,
    )

    # 2) 加密回填存量明文（encrypt_secret 对空值/已加密值幂等）
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(_llmprovider.c.id, _llmprovider.c.api_key, _llmprovider.c.auth_token),
    ).fetchall()
    for row in rows:
        conn.execute(
            _llmprovider.update()
            .where(_llmprovider.c.id == row.id)
            .values(
                api_key=encrypt_secret(row.api_key),
                auth_token=encrypt_secret(row.auth_token),
            ),
        )


def downgrade():
    # 注意：本迁移不支持安全降级。
    # 升级后 api_key/auth_token 存储的是 Fernet 密文（enc:v1: 前缀 + token），
    # 其长度普遍超过 512 字符，且无法在不知道密钥的情况下自动解密回明文。
    # 因此降级仅恢复列类型，存在两个已知问题：
    #   1. 对密文超过 512 字符的行，alter_column 会因 "value too long" 直接失败；
    #   2. 即使长度允许，列中残留的仍是密文，降级后的明文逻辑会把密文当作真实
    #      凭据使用。
    # 如确需降级，应先用配套脚本将凭据解密回明文再执行本函数。
    op.alter_column(
        'llmprovider', 'api_key',
        existing_type=Text(), type_=sa.String(length=512), existing_nullable=False,
    )
    op.alter_column(
        'llmprovider', 'auth_token',
        existing_type=Text(), type_=sa.String(length=512), existing_nullable=False,
    )

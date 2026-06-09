"""
安全模块。

提供 JWT 令牌的创建与解码、密码的哈希与验证功能。
密码哈希使用 Argon2（主）+ Bcrypt（备选）双算法方案。
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# 密码哈希器：优先使用 Argon2，备选 Bcrypt
password_hash = PasswordHash((Argon2Hasher(), BcryptHasher()))

# JWT 签名算法
ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta,
    scope: Literal["access", "refresh", "code"] = "access",
) -> str:
    """创建 JWT 令牌。

    Args:
        subject: 用户标识（通常为 user_id）
        expires_delta: 过期时间增量，如 ``timedelta(minutes=480)``
        scope: 令牌作用域 — access（登录）、refresh（刷新）、code（code-server）

    Returns:
        编码后的 JWT 字符串
    """
    expire = datetime.now(UTC) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject), "scope": scope}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(
    token: str, scope: Literal["access", "refresh", "code"] = "access"
) -> None | dict:
    """解码并验证 JWT 令牌。

    Args:
        token: JWT 字符串
        scope: 期望的令牌作用域，不匹配则返回 None

    Returns:
        成功返回包含 ``sub`` 的 payload 字典，失败返回 None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload["scope"] != scope:
            raise jwt.InvalidTokenError
        return payload
    except jwt.exceptions.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


def get_password_hash(password: str) -> str:
    """对明文密码进行哈希。"""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, str | None]:
    """验证密码，如果哈希算法升级则返回更新后的哈希值。

    Returns:
        (是否验证通过, 更新后的哈希值或 None)
    """
    return password_hash.verify_and_update(plain_password, hashed_password)

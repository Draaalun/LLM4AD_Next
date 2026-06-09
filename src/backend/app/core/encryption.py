"""
敏感字段加密工具。

为数据库中存储的供应商凭据（api_key、auth_token 等）提供对称加密，
避免明文落库。基于 ``cryptography`` 的 Fernet（AES-128-CBC + HMAC）实现，
并提供一个 SQLAlchemy ``TypeDecorator``，在写入时自动加密、读取时自动解密，
对业务层完全透明。

密文格式为 ``enc:v1:<fernet_token>``，带版本前缀以便未来轮换；解密时若发现
值不含该前缀，则视为历史明文原样返回，从而兼容尚未迁移的存量数据。

加密密钥来源（优先级从高到低）：
    1. ``settings.PROVIDER_ENCRYPTION_KEY``（独立配置的密钥）
    2. ``settings.SECRET_KEY``（派生，开箱即用，无需额外配置）

注意：密钥一旦用于加密就不能随意更换，否则已有密文将无法解密。
"""

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

logger = logging.getLogger(__name__)

# 密文版本前缀，便于识别已加密数据及未来密钥轮换
_PREFIX = "enc:v1:"


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    """构造并缓存 Fernet 实例。

    将配置中的密钥源经 SHA-256 派生为 32 字节，再 urlsafe-base64 编码为
    Fernet 所需的密钥格式，从而允许密钥源为任意长度的普通字符串。

    Returns:
        基于当前配置密钥的 Fernet 实例（进程级缓存）。
    """
    key_source = settings.PROVIDER_ENCRYPTION_KEY or settings.SECRET_KEY
    derived = base64.urlsafe_b64encode(hashlib.sha256(key_source.encode()).digest())
    return Fernet(derived)


def encrypt_secret(plaintext: str | None) -> str | None:
    """加密敏感字符串。

    空值（None 或空串）保持原样不加密；已带版本前缀的值视为已加密，原样返回
    以保证幂等。

    Args:
        plaintext: 待加密的明文。

    Returns:
        形如 ``enc:v1:<token>`` 的密文；对空值返回原值。
    """
    if not plaintext:
        return plaintext
    if plaintext.startswith(_PREFIX):
        return plaintext
    token = _fernet().encrypt(plaintext.encode()).decode()
    return _PREFIX + token


def decrypt_secret(value: str | None) -> str | None:
    """解密敏感字符串。

    对空值或不含版本前缀的值（历史明文）原样返回，兼容未迁移数据。解密失败
    （密钥变更或数据损坏）时采取 fail-closed 策略：记录错误并返回空串，而非
    返回密文——避免把无法使用的密文当作 key 发往外部 LLM 服务、写入任务参数
    或日志，从而扩大泄露面；空 key 会触发一个清晰的认证失败，便于定位。

    Args:
        value: 数据库中存储的值（密文或历史明文）。

    Returns:
        解密后的明文；对空值/历史明文返回原值；解密失败返回空串。
    """
    if not value or not value.startswith(_PREFIX):
        return value
    token = value[len(_PREFIX):]
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        logger.error("解密供应商凭据失败，密钥可能已变更或数据已损坏；返回空值")
        return ""


class EncryptedString(TypeDecorator):
    """透明加解密的 SQLAlchemy 字符串类型。

    底层以 ``Text`` 存储（密文比明文长，不设长度上限），写入数据库前自动加密、
    从数据库读取后自动解密，使业务层始终以明文操作字段。
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:  # noqa: ANN001
        """写入数据库前加密。"""
        return encrypt_secret(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:  # noqa: ANN001
        """从数据库读取后解密。"""
        return decrypt_secret(value)

"""任务配置文件的整体对称加解密（宿主写入端与容器读取端共用）。

将写入挂载卷的 AppConfig JSON **整体**加密为单段密文，避免明文落盘后被
容器内运行的用户演化代码读取。整体加密（而非逐字段）可彻底消除「敏感字段
名单维护不全」的风险——凭据无论藏在 ``api_key``、``auth_token`` 还是
``base_url`` 中（如内置 provider 被替换进的 access token）都不会泄漏。

与 :mod:`app.core.encryption` 的区别：

- 本模块**不依赖** ``app.core``（仅依赖 ``cryptography`` 与标准库），可在精简的
  任务容器镜像内导入——该镜像不包含 ``app/core``。
- 使用**每任务一次性随机密钥**（由宿主生成、经环境变量传入容器），而非数据库
  主密钥；主密钥永不进入容器。
"""

import json

from cryptography.fernet import Fernet


def generate_key() -> str:
    """生成一个新的 Fernet 密钥。

    Returns:
        urlsafe-base64 编码的密钥字符串，可直接经环境变量传递。
    """
    return Fernet.generate_key().decode()


def encrypt_config(data: dict, key: str) -> str:
    """将配置字典整体序列化并加密为单段密文。

    Args:
        data: 待写入的配置字典（如 run_args）。
        key: :func:`generate_key` 生成的密钥。

    Returns:
        Fernet 密文字符串，可直接写入文件。
    """
    plaintext = json.dumps(data, ensure_ascii=False, default=str)
    return Fernet(key.encode()).encrypt(plaintext.encode()).decode()


def decrypt_config(token: str, key: str) -> dict:
    """解密由 :func:`encrypt_config` 产生的密文并还原为配置字典。

    Args:
        token: 从挂载卷读取的密文字符串。
        key: 与加密时一致的密钥。

    Returns:
        还原后的配置字典。

    Raises:
        cryptography.fernet.InvalidToken: 密钥不匹配或数据损坏时抛出。
    """
    plaintext = Fernet(key.encode()).decrypt(token.encode()).decode()
    return json.loads(plaintext)

"""
公共基类与通用模型。

包含时间混入类、通用消息模型、令牌模型等与具体业务无关的基础定义。
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class TimeMixin:
    """时间混入类，为数据库模型自动添加创建时间和更新时间字段。"""

    created_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )
    updated_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),
    )


class Message(SQLModel):
    """通用消息响应模型，用于返回简单的文本提示信息。"""

    message: str = Field(default="")


class Token(SQLModel):
    """JWT 令牌响应模型，包含访问令牌和刷新令牌。"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class NewPassword(SQLModel):
    """密码重置请求模型，包含重置令牌和新密码。"""

    token: str
    new_password: str = Field(min_length=8, max_length=128)

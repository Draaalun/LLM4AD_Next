"""
条目（Item）模型。

定义条目数据库模型及其相关的请求/响应 Schema。
条目是用户名下的通用资源，用于演示 CRUD 操作和权限控制。
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TimeMixin  # noqa: F401 — 确保 TimeMixin 在元数据中可用

# ---- 基础 Schema ----


class ItemBase(SQLModel):
    """条目基础 Schema，定义条目的公共字段。"""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# ---- 请求 Schema ----


class ItemCreate(ItemBase):
    """条目创建请求。"""

    pass


class ItemUpdate(ItemBase):
    """条目更新请求（所有字段均可选）。"""

    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# ---- 数据库模型 ----


class Item(ItemBase, table=True):
    """条目数据库模型，通过 owner_id 关联到用户。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    owner: Optional["User"] = Relationship(back_populates="items")  # type: ignore[name-defined]  # noqa: F821


# ---- 响应 Schema ----


class ItemPublic(ItemBase):
    """条目公开信息响应。"""

    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    """条目列表响应，包含分页总数。"""

    data: list[ItemPublic]
    count: int

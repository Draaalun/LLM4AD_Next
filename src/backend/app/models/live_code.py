"""
微信群活码模型。

定义"活码"（LiveCode）与其下挂的"真实二维码"（LiveCodeTarget）数据库模型。

业务背景：微信群二维码有效期仅 7 天，直接分发给用户会很快失效。活码方案为用户
提供一个**永久不变**的二维码（指向后端落地页），而管理员在后台维护一组可随时更换、
带过期时间与人数上限的真实群码；用户扫描永久码时，系统按配置的切换策略动态返回当前
有效的真实群码。这样对外的二维码永不更换，对内的群码可以无限轮换。
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import DateTime, Index, Text
from sqlmodel import Column, Field, Relationship, SQLModel

from app.models.base import TimeMixin


class LiveCodeStrategy(StrEnum):
    """真实群码的切换策略枚举。"""

    SEQUENTIAL = "sequential"  # 顺延：始终用当前这张，直到过期或满员才自动切下一张
    ROUND_ROBIN = "round_robin"  # 轮询：每次扫码在有效群码间均匀轮流分配
    RANDOM = "random"  # 随机：每次扫码从有效群码中随机挑一张


class ContactDisplay(StrEnum):
    """『联系我们』展示模式枚举。

    决定该活码是否、以及如何出现在前端「联系我们」面板。
    """

    NONE = "none"  # 不在联系我们展示
    LANDING = "landing"  # 展示永久码（落地页/可轮换群码，适合会过期的微信群码）
    DIRECT = "direct"  # 直连真实图片（取第一张有效真实码，适合个人微信/公众号等永久码）


# ---- 活码（对外永久二维码）----


class LiveCodeBase(SQLModel):
    """活码基础 Schema，定义对外展示与行为相关的公共字段。"""

    name: str = Field(max_length=255, description="活码名称（仅后台管理可见）")
    description: str | None = Field(
        default=None, sa_column=Column(Text), description="活码备注说明（仅后台可见）"
    )
    strategy: LiveCodeStrategy = Field(
        default=LiveCodeStrategy.SEQUENTIAL, description="真实群码切换策略"
    )
    landing_title: str | None = Field(
        default=None, max_length=255, description="落地页主标题，如『扫码加入交流群』"
    )
    landing_tip: str | None = Field(
        default=None, max_length=512, description="落地页引导文案，如『长按二维码，识别加入群聊』"
    )
    is_active: bool = Field(default=True, description="是否启用；停用后扫码展示停用提示")


class LiveCode(LiveCodeBase, TimeMixin, table=True):
    """活码数据库模型。

    一个活码对应一张永久二维码，下挂多张可轮换的真实群码（``targets``）。
    """

    __tablename__ = "live_code"
    __table_args__ = (
        Index("ix_live_code_created_time", "created_time"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    slug: str = Field(
        max_length=32, unique=True, index=True, description="公开短码，构成永久落地页 URL"
    )
    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        index=True,
        description="创建者用户 ID",
    )
    rotation_cursor: int = Field(default=0, description="轮询策略游标，记录下一个分配位置")
    total_scans: int = Field(default=0, description="累计扫码次数（统计用）")
    contact_display: ContactDisplay = Field(
        default=ContactDisplay.NONE,
        index=True,
        description="『联系我们』展示模式：none 不展示 / landing 永久码 / direct 真实图片（可多个并存）",
    )

    # 关系：级联删除真实群码
    targets: list["LiveCodeTarget"] = Relationship(
        back_populates="live_code",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "LiveCodeTarget.sort_order, LiveCodeTarget.created_time"},
    )


# ---- 真实群码（对内可轮换的真实二维码）----


class LiveCodeTargetBase(SQLModel):
    """真实群码基础 Schema，定义有效性控制相关的公共字段。"""

    label: str | None = Field(default=None, max_length=255, description="备注，如『1 群』")
    expires_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        description="过期时间；为空表示永不过期。微信群码建议设为 7 天后",
    )
    scan_limit: int | None = Field(
        default=None, description="扫码次数上限（近似人数）；为空表示不限。达到上限自动切下一张"
    )
    is_enabled: bool = Field(default=True, description="是否启用该群码")
    sort_order: int = Field(default=0, description="排序/顺延序号，越小越优先")


class LiveCodeTarget(LiveCodeTargetBase, TimeMixin, table=True):
    """真实群码数据库模型。

    存储单张真实微信群二维码图片（落在对象存储）及其有效性控制字段。
    """

    __tablename__ = "live_code_target"
    __table_args__ = (
        Index("ix_live_code_target_live_code_id", "live_code_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    live_code_id: uuid.UUID = Field(
        foreign_key="live_code.id", ondelete="CASCADE", description="所属活码 ID"
    )
    image_key: str = Field(max_length=1024, description="真实群码图片在对象存储中的 key")
    content_type: str = Field(default="image/png", max_length=128, description="图片 MIME 类型")
    original_filename: str | None = Field(
        default=None, max_length=512, description="上传时的原始文件名"
    )
    scan_count: int = Field(default=0, description="该群码已被分配的扫码次数")

    # 关系：所属活码
    live_code: Optional["LiveCode"] = Relationship(back_populates="targets")

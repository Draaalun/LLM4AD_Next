"""
意见反馈模型。

定义用户反馈的数据库模型，包括反馈类型、状态、优先级等企业级字段。
支持反馈的全生命周期管理，从提交到处理完成。
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import DateTime, Index, Text
from sqlmodel import Column, Field, Relationship, SQLModel

from app.models.base import TimeMixin


class FeedbackType(StrEnum):
    """反馈类型枚举。"""

    BUG = "bug"  # 错误报告
    FEATURE = "feature"  # 功能建议
    IMPROVEMENT = "improvement"  # 改进建议
    QUESTION = "question"  # 问题咨询
    OTHER = "other"  # 其他


class FeedbackStatus(StrEnum):
    """反馈状态枚举。"""

    PENDING = "pending"  # 待处理
    IN_PROGRESS = "in_progress"  # 处理中
    RESOLVED = "resolved"  # 已解决
    CLOSED = "closed"  # 已关闭
    REJECTED = "rejected"  # 已拒绝


class FeedbackPriority(StrEnum):
    """反馈优先级枚举。"""

    LOW = "low"  # 低优先级
    MEDIUM = "medium"  # 中优先级
    HIGH = "high"  # 高优先级
    URGENT = "urgent"  # 紧急


# ---- 意见反馈 ----


class FeedbackBase(SQLModel):
    """意见反馈基础 Schema，定义反馈的公共字段。"""

    type: FeedbackType = Field(default=FeedbackType.OTHER, description="反馈类型")
    title: str = Field(max_length=255, description="反馈标题")
    content: str = Field(sa_column=Column(Text, nullable=False), description="反馈详细内容")
    contact_email: str | None = Field(
        default=None, max_length=255, description="联系邮箱（可选）"
    )
    contact_phone: str | None = Field(
        default=None, max_length=50, description="联系电话（可选）"
    )
    browser_info: str | None = Field(
        default=None, max_length=512, description="浏览器信息"
    )
    page_url: str | None = Field(
        default=None, max_length=1024, description="反馈页面 URL"
    )
    screenshot_url: str | None = Field(
        default=None, max_length=1024, description="截图 URL（可选）"
    )
    attachments: str | None = Field(
        default=None, sa_column=Column(Text), description="附件 URL 列表（JSON 格式）"
    )


class Feedback(FeedbackBase, TimeMixin, table=True):
    """意见反馈数据库模型。

    存储用户提交的反馈信息，包括反馈内容、状态、优先级等。
    支持管理员回复和状态跟踪。
    """

    __tablename__ = "feedback"
    __table_args__ = (
        Index("ix_feedback_type", "type"),
        Index("ix_feedback_created_time", "created_time"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", index=True, description="提交用户 ID（匿名反馈时为空）"
    )
    status: FeedbackStatus = Field(
        default=FeedbackStatus.PENDING, index=True, description="反馈状态"
    )
    priority: FeedbackPriority = Field(
        default=FeedbackPriority.MEDIUM, description="反馈优先级"
    )
    admin_reply: str | None = Field(
        default=None, sa_column=Column(Text), description="管理员回复"
    )
    admin_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", description="处理管理员 ID"
    )
    resolved_time: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), description="解决时间"
    )
    tags: str | None = Field(
        default=None, max_length=512, description="标签（逗号分隔）"
    )
    internal_notes: str | None = Field(
        default=None, sa_column=Column(Text), description="内部备注（用户不可见）"
    )

    # 关系
    user: Optional["User"] = Relationship(  # type: ignore # noqa: F821
        sa_relationship_kwargs={"foreign_keys": "[Feedback.user_id]"}
    )
    admin: Optional["User"] = Relationship(  # type: ignore # noqa: F821
        sa_relationship_kwargs={"foreign_keys": "[Feedback.admin_id]"}
    )


class FeedbackCreate(FeedbackBase):
    """创建反馈请求模型。"""

    pass


class FeedbackUpdate(SQLModel):
    """更新反馈请求模型（管理员使用）。"""

    status: FeedbackStatus | None = None
    priority: FeedbackPriority | None = None
    admin_reply: str | None = None
    tags: str | None = None
    internal_notes: str | None = None


class FeedbackPublic(FeedbackBase):
    """反馈公开响应模型（用户视图）。"""

    id: uuid.UUID
    user_id: uuid.UUID | None
    status: FeedbackStatus
    priority: FeedbackPriority
    admin_reply: str | None
    resolved_time: datetime | None
    tags: str | None
    created_time: datetime
    updated_time: datetime
    user_email: str | None = Field(default=None, description="提交人邮箱")
    user_full_name: str | None = Field(default=None, description="提交人姓名")


class FeedbackAdmin(FeedbackPublic):
    """反馈管理员响应模型（包含内部信息）。"""

    admin_id: uuid.UUID | None
    internal_notes: str | None


class FeedbacksPublic(SQLModel):
    """反馈列表响应模型。"""

    items: list[FeedbackPublic]
    total: int
    skip: int
    limit: int


class FeedbackStatistics(SQLModel):
    """反馈统计信息模型。"""

    total: int = Field(description="总反馈数")
    pending: int = Field(description="待处理数")
    in_progress: int = Field(description="处理中数")
    resolved: int = Field(description="已解决数")
    closed: int = Field(description="已关闭数")
    rejected: int = Field(description="已拒绝数")
    by_type: dict[str, int] = Field(description="按类型统计")
    by_priority: dict[str, int] = Field(description="按优先级统计")

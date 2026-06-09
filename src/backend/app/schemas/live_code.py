"""
微信群活码 API Schema。

定义活码管理端与公开扫码端的请求/响应模型。与 ORM 模型解耦，
仅承载 HTTP 层的数据形状。
"""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.live_code import ContactDisplay, LiveCodeStrategy

# ---- 活码（管理端）----


class LiveCodeCreate(SQLModel):
    """创建活码请求体。"""

    name: str = Field(max_length=255, description="活码名称")
    description: str | None = Field(default=None, description="备注说明")
    strategy: LiveCodeStrategy = Field(
        default=LiveCodeStrategy.SEQUENTIAL, description="真实群码切换策略"
    )
    landing_title: str | None = Field(default=None, max_length=255, description="落地页主标题")
    landing_tip: str | None = Field(default=None, max_length=512, description="落地页引导文案")


class LiveCodeUpdate(SQLModel):
    """更新活码请求体，所有字段可选。"""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    strategy: LiveCodeStrategy | None = None
    landing_title: str | None = Field(default=None, max_length=255)
    landing_tip: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None
    contact_display: ContactDisplay | None = None


# ---- 真实群码（管理端）----


class TargetUpdate(SQLModel):
    """更新真实群码请求体，所有字段可选。"""

    label: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None
    scan_limit: int | None = Field(default=None, ge=0)
    is_enabled: bool | None = None
    sort_order: int | None = None


class TargetPublic(SQLModel):
    """真实群码响应模型（管理端视图）。"""

    id: uuid.UUID
    label: str | None
    expires_at: datetime | None
    scan_limit: int | None
    scan_count: int
    is_enabled: bool
    sort_order: int
    created_time: datetime
    image_url: str = Field(description="后台预览图片的相对 API 路径")
    is_valid: bool = Field(description="当前是否可用（启用且未过期未满员）")
    status: str = Field(description="人类可读状态：valid / disabled / expired / full")


# ---- 活码响应 ----


class LiveCodePublic(SQLModel):
    """活码响应模型（列表/详情公共部分）。"""

    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    strategy: LiveCodeStrategy
    landing_title: str | None
    landing_tip: str | None
    is_active: bool
    contact_display: ContactDisplay = Field(
        description="『联系我们』展示模式：none/landing/direct"
    )
    total_scans: int
    created_time: datetime
    updated_time: datetime
    public_url: str = Field(description="对外永久落地页 URL（永久二维码所编码的内容）")
    qrcode_url: str = Field(description="下载永久二维码 PNG 的相对 API 路径")
    target_count: int = Field(description="真实群码总数")
    valid_target_count: int = Field(description="当前有效的真实群码数量")
    creator_email: str | None = Field(default=None, description="创建者邮箱")
    creator_name: str | None = Field(default=None, description="创建者姓名")


class LiveCodeDetail(LiveCodePublic):
    """活码详情响应模型，附带真实群码列表。"""

    targets: list[TargetPublic] = Field(default_factory=list)


class PaginatedLiveCode(SQLModel):
    """活码分页列表响应模型。"""

    items: list[LiveCodePublic]
    total: int
    skip: int
    limit: int


class LiveCodeContactInfo(SQLModel):
    """『联系我们』活码公开信息（免鉴权）。

    仅暴露展示所需的最小字段，供前端拉取并渲染二维码与引导文案。
    ``image_url`` 已由后端按展示模式解析：landing 为永久码 PNG，direct 为真实图片。
    """

    slug: str = Field(description="公开短码")
    landing_title: str | None = Field(default=None, description="展示标题")
    landing_tip: str | None = Field(default=None, description="引导文案")
    display: ContactDisplay = Field(description="展示模式：landing 永久码 / direct 真实图片")
    image_url: str = Field(
        description="最终展示图片的公开 URL（可直接用于 img）；direct 无有效真实码时为空串"
    )

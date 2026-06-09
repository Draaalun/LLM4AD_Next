"""进化块分析建议（Advisor）相关的请求/响应 Schema 定义。"""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.report import ReportStatus


class AdvisorGenerateRequest(BaseModel):
    """进化块分析建议生成请求体。

    Attributes:
        goal: 算法演化目标描述。
        language: 输出语言。
        provider_id: LLM Provider ID，格式同 ReportGenerateRequest。
        model_name: 指定模型名称，覆盖 Provider 默认模型。
    """

    goal: str = Field(description="算法演化目标描述")
    language: Literal["zh", "en"] = Field(
        default="en",
        description="输出语言：'zh' 表示中文，'en' 表示英文",
    )
    provider_id: str | None = Field(
        default=None,
        description="LLM Provider ID；支持 null/'default'/'mock'/真实UUID",
    )
    model_name: str | None = Field(
        default=None,
        description="指定使用的模型名称；未提供时使用 Provider 默认模型",
    )


class AdvisorGenerateResponse(BaseModel):
    """触发进化块分析建议生成后的响应体。"""

    task_id: uuid.UUID
    advisor_type: str = Field(description="'block_advise' 或 'block_recommend'")
    status: ReportStatus
    message: str


class AdvisorDetailResponse(BaseModel):
    """获取进化块分析建议结果的响应体。"""

    task_id: uuid.UUID
    advisor_type: str
    status: ReportStatus | None = None
    data: Any = Field(default=None, description="分析结果数据")
    error: str | None = None
    updated_at: str | None = None

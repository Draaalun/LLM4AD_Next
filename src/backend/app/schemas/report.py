"""演化分析报告相关的请求/响应 Schema 定义。"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ReportType(StrEnum):
    """报告类型枚举。

    Attributes:
        TECH_CHANGE: 技术演化变更报告。
        NODE_COMPARISON: 节点对比报告。
        CHAIN_ANALYSIS: 演化链路分析报告。
        CHAMPION_BIRTH: 冠军算法诞生报告。
    """

    TECH_CHANGE = "tech_change"
    NODE_COMPARISON = "node_comparison"
    CHAIN_ANALYSIS = "chain_analysis"
    CHAMPION_BIRTH = "champion_birth"


class ReportStatus(StrEnum):
    """报告生成状态枚举。

    Attributes:
        GENERATING: 生成中。
        COMPLETED: 生成完成。
        FAILED: 生成失败。
        CANCELLED: 已取消。
    """

    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---- 请求 Schema ----


class ReportGenerateRequest(BaseModel):
    """报告生成请求体。

    根据 ``report_type`` 不同，需要传入对应的额外参数：

    * ``NODE_COMPARISON`` / ``CHAIN_ANALYSIS``：必须提供至少 2 个 ``node_ids``。
    * ``CHAMPION_BIRTH``：必须提供 ``best_node_id``。
    """

    report_type: ReportType = Field(description="待生成的报告类型")
    language: Literal["zh", "en"] = Field(
        default="zh",
        description="输出语言：'zh' 表示中文，'en' 表示英文",
    )
    provider_id: str | None = Field(
        default=None,
        description="LLM Provider ID；支持传空字符串/null（使用用户默认）、'default'（使用用户默认）、'mock'（mock模式）、真实的供应商UUID",
    )
    model_name: str | None = Field(
        default=None,
        description="指定使用的模型名称；未提供时使用 Provider 默认模型",
    )
    prompt_template: str | None = Field(
        default=None,
        description="自定义 Prompt 模板；未提供时使用内置默认模板",
    )
    node_ids: list[str] | None = Field(
        default=None,
        description="节点 ID 列表，用于 node_comparison 与 chain_analysis 报告",
    )
    best_node_id: str | None = Field(
        default=None,
        description="最佳节点 ID，用于 champion_birth 报告",
    )

    @model_validator(mode="after")
    def validate_params_for_type(self) -> "ReportGenerateRequest":
        """校验各报告类型所需的特有参数是否齐全。

        Returns:
            通过校验后的请求对象自身。

        Raises:
            ValueError: 当对应报告类型缺少必要参数时抛出。
        """
        if self.report_type == ReportType.NODE_COMPARISON:
            if not self.node_ids or len(self.node_ids) < 2:
                raise ValueError(
                    "node_comparison requires at least 2 node_ids"
                )
        elif self.report_type == ReportType.CHAIN_ANALYSIS:
            if not self.node_ids or len(self.node_ids) < 2:
                raise ValueError(
                    "chain_analysis requires at least 2 node_ids"
                )
        elif self.report_type == ReportType.CHAMPION_BIRTH:
            if not self.best_node_id:
                raise ValueError("champion_birth requires best_node_id")
        return self


# ---- 响应 Schema ----


class ReportEntry(BaseModel):
    """存储于 ``task.reports`` 字典中的单条报告条目。

    Attributes:
        status: 当前生成状态。
        content: 报告正文内容（成功时存在）。
        created_at: 创建时间。
        updated_at: 最近一次更新时间。
        error: 错误信息（失败时存在）。
        provider_model: 实际使用的 LLM 模型名称。
        params: 生成报告时使用的参数快照。
    """

    status: ReportStatus
    content: str | None = None
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    provider_model: str | None = None
    params: dict = Field(default_factory=dict)


class ReportGenerateResponse(BaseModel):
    """触发报告生成后的响应体。"""

    task_id: uuid.UUID
    report_type: ReportType
    status: ReportStatus
    message: str


class ReportDetailResponse(BaseModel):
    """获取指定报告详情的响应体。"""

    task_id: uuid.UUID
    report_type: ReportType
    report: ReportEntry | None = None


class ReportStopResponse(BaseModel):
    """停止报告生成后的响应体。"""

    task_id: uuid.UUID
    report_type: ReportType
    status: ReportStatus
    message: str


class ReportTemplateItem(BaseModel):
    """单个报告类型的 Prompt 模板信息。"""

    user_prompt_template: str = Field(
        description="User prompt 模板，变量用 {variable_name} 标记"
    )
    variables: list[str] = Field(
        description="模板中可用的变量名列表"
    )


class ReportTemplatesResponse(BaseModel):
    """所有报告类型的 Prompt 模板响应体。"""

    templates: dict[str, ReportTemplateItem]

"""Test configuration for frontend UI form generation.

Inherits from AppConfig and adds synthetic fields that exercise every
ui() parameter combination the frontend must handle:
  - All primitive types (str, int, float, bool)
  - Optional / nullable fields
  - Literal enums and Python Enum
  - Nested BaseModel (single and list)
  - Discriminated unions
  - dict, list[str], list[int], list[nested]
  - Constrained numerics (ge, le, gt, lt, multiple_of)
  - Fields with user_required, is_path, hidden
  - Fields with and without defaults
"""

from enum import Enum
from typing import Any, Literal

from llm4ad.config.app import AppConfig
from llm4ad.config.ui import ui
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------

class TagConfig(BaseModel):
    """Simple leaf-level nested model."""

    key: str = Field(
        ..., description="Tag key",
        json_schema_extra=ui(
            required=True, order=0, user_required=True,
            label_zh="标签键", label_en="Tag Key",
            desc_zh="标签的唯一键名", desc_en="Unique key for the tag",
        ),
    )
    value: str = Field(
        default="", description="Tag value",
        json_schema_extra=ui(
            order=1,
            label_zh="标签值", label_en="Tag Value",
            desc_zh="标签对应的值", desc_en="Value associated with the tag",
        ),
    )


class ThresholdConfig(BaseModel):
    """Nested model with constrained numerics and optional fields."""

    min_value: float = Field(
        default=0.0, ge=0.0, le=1.0,
        json_schema_extra=ui(
            order=0,
            label_zh="最小值", label_en="Min Value",
            desc_zh="阈值下限，范围 0.0-1.0",
            desc_en="Lower bound of the threshold, range 0.0-1.0",
        ),
    )
    max_value: float = Field(
        default=1.0, ge=0.0, le=1.0,
        json_schema_extra=ui(
            order=1,
            label_zh="最大值", label_en="Max Value",
            desc_zh="阈值上限，范围 0.0-1.0",
            desc_en="Upper bound of the threshold, range 0.0-1.0",
        ),
    )
    step: float | None = Field(
        default=None, ge=0.001, le=1.0,
        json_schema_extra=ui(
            order=2,
            label_zh="步长", label_en="Step",
            desc_zh="可选的步长值，为空则使用默认步长",
            desc_en="Optional step size; None uses the default step",
        ),
    )
    enabled: bool = Field(
        default=True,
        json_schema_extra=ui(
            order=3,
            label_zh="启用", label_en="Enabled",
            desc_zh="是否启用此阈值配置",
            desc_en="Whether this threshold config is active",
        ),
    )


class ScheduleConfig(BaseModel):
    """Nested model with mixed types for testing complex nesting."""

    cron_expression: str = Field(
        default="0 * * * *",
        json_schema_extra=ui(
            order=0, user_required=True,
            label_zh="Cron 表达式", label_en="Cron Expression",
            desc_zh="标准 cron 表达式，定义调度周期",
            desc_en="Standard cron expression defining the schedule",
        ),
    )
    timezone: str = Field(
        default="UTC",
        json_schema_extra=ui(
            order=1,
            label_zh="时区", label_en="Timezone",
            desc_zh="调度使用的时区", desc_en="Timezone for the schedule",
        ),
    )
    max_runs: int | None = Field(
        default=None, ge=1,
        json_schema_extra=ui(
            order=2,
            label_zh="最大运行次数", label_en="Max Runs",
            desc_zh="最大运行次数，为空则无限制",
            desc_en="Maximum number of runs; None means unlimited",
        ),
    )
    retry_delays: list[int] = Field(
        default_factory=lambda: [1, 5, 30],
        json_schema_extra=ui(
            order=3,
            label_zh="重试延迟列表", label_en="Retry Delays",
            desc_zh="每次重试的延迟秒数列表",
            desc_en="List of delay seconds for each retry attempt",
        ),
    )
    thresholds: ThresholdConfig = Field(
        default_factory=ThresholdConfig,
        json_schema_extra=ui(
            order=4,
            label_zh="阈值配置", label_en="Thresholds",
            desc_zh="嵌套的阈值配置对象",
            desc_en="Nested threshold configuration object",
        ),
    )


# ---------------------------------------------------------------------------
# Discriminated union variants
# ---------------------------------------------------------------------------

class NotifyEmailConfig(BaseModel):
    """Email notification variant."""

    type: Literal["email"] = Field(
        default="email",
        json_schema_extra=ui(
            required=True, order=0, hidden=True,
            label_zh="类型", label_en="Type",
            desc_zh="通知类型标识", desc_en="Notification type identifier",
        ),
    )
    recipients: list[str] = Field(
        default_factory=list,
        json_schema_extra=ui(
            order=1, user_required=True,
            label_zh="收件人列表", label_en="Recipients",
            desc_zh="邮件通知的收件人地址列表",
            desc_en="List of email addresses to notify",
        ),
    )
    subject_template: str = Field(
        default="[LLM4AD] {event}",
        json_schema_extra=ui(
            order=2,
            label_zh="主题模板", label_en="Subject Template",
            desc_zh="邮件主题模板，支持 {event} 占位符",
            desc_en="Email subject template with {event} placeholder",
        ),
    )


class NotifyWebhookConfig(BaseModel):
    """Webhook notification variant."""

    type: Literal["webhook"] = Field(
        default="webhook",
        json_schema_extra=ui(
            required=True, order=0, hidden=True,
            label_zh="类型", label_en="Type",
            desc_zh="通知类型标识", desc_en="Notification type identifier",
        ),
    )
    url: str = Field(
        ..., description="Webhook URL",
        json_schema_extra=ui(
            required=True, order=1, user_required=True,
            label_zh="Webhook 地址", label_en="Webhook URL",
            desc_zh="接收通知的 Webhook 端点地址",
            desc_en="Webhook endpoint URL to receive notifications",
        ),
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra=ui(
            order=2,
            label_zh="请求头", label_en="Headers",
            desc_zh="附加到 Webhook 请求的自定义 HTTP 头",
            desc_en="Custom HTTP headers attached to webhook requests",
        ),
    )
    timeout: float = Field(
        default=10.0, gt=0, le=120,
        json_schema_extra=ui(
            order=3,
            label_zh="超时时间", label_en="Timeout",
            desc_zh="Webhook 请求超时秒数（0-120）",
            desc_en="Webhook request timeout in seconds (0-120)",
        ),
    )


# ---------------------------------------------------------------------------
# Enum for testing
# ---------------------------------------------------------------------------

class Priority(str, Enum):  # noqa: UP042
    """Python str enum for testing enum rendering."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Main test config
# ---------------------------------------------------------------------------

class TestUIConfig(BaseModel):
    """Extended AppConfig with synthetic fields for UI testing.

    Covers every combination of field type, optionality, nesting,
    and ui() parameter that the frontend form generator must handle.
    """

    # --- Simple primitives with various ui flags ---

    test_string_required: str = Field(
        ..., description="A required string with no default",
        json_schema_extra=ui(
            required=True, order=100, user_required=True,
            label_zh="必填字符串", label_en="Required String",
            desc_zh="没有默认值的必填字符串字段",
            desc_en="A required string field with no default value",
        ),
    )
    test_string_optional: str | None = Field(
        default=None,
        json_schema_extra=ui(
            order=101,
            label_zh="可选字符串", label_en="Optional String",
            desc_zh="可以为 None 的字符串字段",
            desc_en="A string field that can be None",
        ),
    )
    test_string_hidden: str = Field(
        default="internal_value",
        json_schema_extra=ui(
            order=102, hidden=True,
            label_zh="隐藏字符串", label_en="Hidden String",
            desc_zh="前端不显示的隐藏字段",
            desc_en="A hidden field not shown on the frontend form",
        ),
    )
    test_path_field: str = Field(
        default="/tmp/output",
        json_schema_extra=ui(
            order=103, is_path=True,
            label_zh="输出路径", label_en="Output Path",
            desc_zh="文件系统路径，前端应显示路径选择器",
            desc_en="Filesystem path; frontend should show a path picker",
        ),
    )
    test_path_optional: str | None = Field(
        default=None,
        json_schema_extra=ui(
            order=104, is_path=True,
            label_zh="可选路径", label_en="Optional Path",
            desc_zh="可选的文件路径，为空则不使用",
            desc_en="Optional file path; None means not used",
        ),
    )

    # --- Numeric types with constraints ---

    test_int_basic: int = Field(
        default=42, ge=0, le=1000,
        json_schema_extra=ui(
            order=110,
            label_zh="基础整数", label_en="Basic Integer",
            desc_zh="带范围约束的整数（0-1000）",
            desc_en="Integer with range constraint (0-1000)",
        ),
    )
    test_int_optional: int | None = Field(
        default=None, ge=1,
        json_schema_extra=ui(
            order=111,
            label_zh="可选整数", label_en="Optional Integer",
            desc_zh="可以为 None 的整数字段",
            desc_en="An integer field that can be None",
        ),
    )
    test_float_constrained: float = Field(
        default=0.5, gt=0.0, lt=1.0,
        json_schema_extra=ui(
            order=112,
            label_zh="约束浮点数", label_en="Constrained Float",
            desc_zh="严格大于 0 且小于 1 的浮点数",
            desc_en="Float strictly between 0 and 1 (exclusive)",
        ),
    )
    test_float_with_step: float = Field(
        default=100.0, ge=0.0, multiple_of=0.5,
        json_schema_extra=ui(
            order=113,
            label_zh="步进浮点数", label_en="Stepped Float",
            desc_zh="必须是 0.5 的倍数的浮点数",
            desc_en="Float that must be a multiple of 0.5",
        ),
    )

    # --- Boolean ---

    test_bool: bool = Field(
        default=False,
        json_schema_extra=ui(
            order=120,
            label_zh="布尔开关", label_en="Boolean Toggle",
            desc_zh="简单的布尔开关字段",
            desc_en="A simple boolean toggle field",
        ),
    )

    # --- Literal and Enum ---

    test_literal: Literal["option_a", "option_b", "option_c"] = Field(
        default="option_a",
        json_schema_extra=ui(
            order=130,
            label_zh="字面量选择", label_en="Literal Choice",
            desc_zh="从固定选项中选择一个值",
            desc_en="Select one value from a fixed set of options",
        ),
    )
    test_literal_optional: Literal["x", "y", "z"] | None = Field(
        default=None,
        json_schema_extra=ui(
            order=131,
            label_zh="可选字面量", label_en="Optional Literal",
            desc_zh="可以为 None 的字面量选择字段",
            desc_en="A literal choice field that can be None",
        ),
    )
    test_enum: Priority = Field(
        default=Priority.MEDIUM,
        json_schema_extra=ui(
            order=132,
            label_zh="优先级枚举", label_en="Priority Enum",
            desc_zh="使用 Python Enum 的优先级选择",
            desc_en="Priority selection using a Python Enum",
        ),
    )

    # --- List types ---

    test_list_str: list[str] = Field(
        default_factory=list,
        json_schema_extra=ui(
            order=140,
            label_zh="字符串列表", label_en="String List",
            desc_zh="字符串值的列表",
            desc_en="A list of string values",
        ),
    )
    test_list_int: list[int] = Field(
        default_factory=lambda: [1, 2, 3],
        json_schema_extra=ui(
            order=141,
            label_zh="整数列表", label_en="Integer List",
            desc_zh="带默认值的整数列表",
            desc_en="A list of integers with default values",
        ),
    )
    test_list_float_optional: list[float] | None = Field(
        default=None,
        json_schema_extra=ui(
            order=142,
            label_zh="可选浮点列表", label_en="Optional Float List",
            desc_zh="可以为 None 的浮点数列表",
            desc_en="A list of floats that can be None",
        ),
    )

    # --- Dict types ---

    test_dict_str: dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra=ui(
            order=150,
            label_zh="字符串字典", label_en="String Dict",
            desc_zh="键值均为字符串的字典",
            desc_en="A dictionary with string keys and string values",
        ),
    )
    test_dict_any: dict[str, Any] = Field(
        default_factory=dict,
        json_schema_extra=ui(
            order=151,
            label_zh="任意值字典", label_en="Any Dict",
            desc_zh="键为字符串、值为任意类型的字典",
            desc_en="A dictionary with string keys and any-type values",
        ),
    )
    test_dict_optional: dict[str, int] | None = Field(
        default=None,
        json_schema_extra=ui(
            order=152,
            label_zh="可选整数字典", label_en="Optional Int Dict",
            desc_zh="可以为 None 的整数值字典",
            desc_en="A dictionary of int values that can be None",
        ),
    )

    # --- Nested BaseModel (single) ---

    test_nested_single: TagConfig = Field(
        default_factory=lambda: TagConfig(key="default"),
        json_schema_extra=ui(
            order=160,
            label_zh="单个嵌套对象", label_en="Single Nested Object",
            desc_zh="单个嵌套的 BaseModel 对象",
            desc_en="A single nested BaseModel object",
        ),
    )
    test_nested_optional: ThresholdConfig | None = Field(
        default=None,
        json_schema_extra=ui(
            order=161,
            label_zh="可选嵌套对象", label_en="Optional Nested Object",
            desc_zh="可以为 None 的嵌套 BaseModel 对象",
            desc_en="A nested BaseModel object that can be None",
        ),
    )
    test_nested_deep: ScheduleConfig = Field(
        default_factory=ScheduleConfig,
        json_schema_extra=ui(
            order=162,
            label_zh="深层嵌套对象", label_en="Deep Nested Object",
            desc_zh="包含多层嵌套的复杂配置对象",
            desc_en="A complex config object with multiple nesting levels",
        ),
    )

    # --- Nested BaseModel (list) ---

    test_nested_list: list[TagConfig] = Field(
        default_factory=list,
        json_schema_extra=ui(
            order=170,
            label_zh="嵌套对象列表", label_en="Nested Object List",
            desc_zh="BaseModel 对象的列表，可动态增删",
            desc_en="A list of BaseModel objects; can be added or removed",
        ),
    )
    test_nested_list_with_defaults: list[ThresholdConfig] = Field(
        default_factory=lambda: [
            ThresholdConfig(min_value=0.0, max_value=0.5),
            ThresholdConfig(min_value=0.5, max_value=1.0),
        ],
        json_schema_extra=ui(
            order=171,
            label_zh="带默认值的嵌套列表", label_en="Nested List with Defaults",
            desc_zh="带有预设默认项的嵌套对象列表",
            desc_en="A nested object list with preset default items",
        ),
    )
    test_nested_list_optional: list[ScheduleConfig] | None = Field(
        default=None,
        json_schema_extra=ui(
            order=172,
            label_zh="可选嵌套列表", label_en="Optional Nested List",
            desc_zh="可以为 None 的嵌套对象列表",
            desc_en="A nested object list that can be None",
        ),
    )

    # --- Discriminated union ---

    test_union: NotifyEmailConfig | NotifyWebhookConfig = Field(
        default_factory=NotifyEmailConfig,
        discriminator="type",
        json_schema_extra=ui(
            order=180,
            label_zh="通知方式（联合类型）", label_en="Notification (Union)",
            desc_zh="通过 type 字段区分的联合类型配置",
            desc_en="Discriminated union config selected by the type field",
        ),
    )
    test_union_optional: NotifyEmailConfig | NotifyWebhookConfig | None = Field(
        default=None,
        discriminator="type",
        json_schema_extra=ui(
            order=181,
            label_zh="可选联合类型", label_en="Optional Union",
            desc_zh="可以为 None 的联合类型配置",
            desc_en="A discriminated union config that can be None",
        ),
    )

    # --- Combination: user_required + is_path + required ---

    test_user_required_path: str = Field(
        ..., description="A required path that the user must fill in",
        json_schema_extra=ui(
            required=True, order=190,
            user_required=True, is_path=True,
            label_zh="必填用户路径", label_en="Required User Path",
            desc_zh="用户必须手动填写的文件路径",
            desc_en="A file path that the user must manually provide",
        ),
    )
class NewAppConfig(AppConfig):
    evaluator:TestUIConfig=Field(
        ui(
            order=181,
            label_zh="可选联合类型", label_en="Optional Union",
            desc_zh="可以为 None 的联合类型配置",
            desc_en="A discriminated union config that can be None",
        ),
    )

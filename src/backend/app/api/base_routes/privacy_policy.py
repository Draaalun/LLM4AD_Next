"""
隐私协议路由。

提供隐私协议内容获取、同意隐私协议等端点。
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import EmailStr
from sqlmodel import SQLModel

from app.api.deps import CurrentUser, SessionDep
from app.crud import user as crud
from app.models import Message, UserPublic

router = APIRouter(prefix="/privacy-policy", tags=["privacy-policy"])

# 获取资源文件目录
_RESOURCES_DIR = Path(__file__).parent.parent / "resources"


def _load_privacy_policy_content(lang: str) -> tuple[str, str]:
    """加载指定语言的隐私协议内容。

    Args:
        lang: 语言代码（zh/en）。

    Returns:
        tuple[str, str]: (content, updated_at)。

    Raises:
        ValueError: 不支持的语言。
    """
    if lang == "en":
        file_path = _RESOURCES_DIR / "privacy_policy_en.md"
    elif lang == "zh":
        file_path = _RESOURCES_DIR / "privacy_policy_zh.md"
    else:
        raise ValueError(f"Unsupported language: {lang}")

    if not file_path.exists():
        raise RuntimeError(f"Privacy policy file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    # 从文件名提取版本或使用固定版本
    version = "1.0.0"
    return content, version


class PrivacyPolicyContent(SQLModel):
    """隐私协议内容响应。"""

    title: str
    content: str
    version: str
    updated_at: str


class AcceptPrivacyPolicyRequest(SQLModel):
    """登录前同意隐私协议请求（需要邮箱密码验证）。"""

    email: EmailStr
    password: str


@router.get("/content", response_model=PrivacyPolicyContent)
def get_privacy_policy_content(lang: str = Query(default="zh", regex="^(zh|en)$")) -> Any:
    """获取隐私协议内容。

    Args:
        lang: 语言代码，支持 zh（中文）和 en（英文）。

    Returns:
        PrivacyPolicyContent: 隐私协议内容及版本信息。
    """
    content, version = _load_privacy_policy_content(lang)
    title = "LLM4AD Privacy Policy" if lang == "en" else "LLM4AD 隐私协议"
    return PrivacyPolicyContent(
        title=title,
        version=version,
        updated_at="2026-05-22",
        content=content,
    )


@router.post("/accept", response_model=Message)
def accept_privacy_policy_authenticated(*, session: SessionDep, current_user: CurrentUser) -> Any:
    """已登录用户同意隐私协议。

    用于已登录但未同意隐私协议的老用户。

    Args:
        session: 数据库会话依赖。
        current_user: 当前登录用户。

    Returns:
        Message: 操作结果提示。

    Raises:
        HTTPException: 已同意过隐私协议（400）。
    """
    if current_user.privacy_policy_accepted:
        raise HTTPException(status_code=400, detail="您已同意过隐私协议")

    current_user.privacy_policy_accepted = True
    current_user.privacy_policy_accepted_at = datetime.now(UTC)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return Message(message="隐私协议同意成功")


@router.post("/accept-before-login", response_model=UserPublic)
def accept_privacy_policy_before_login(*, session: SessionDep, request: AcceptPrivacyPolicyRequest) -> Any:
    """登录前同意隐私协议。

    用于登录时发现未同意隐私协议的用户，通过邮箱密码验证身份后同意。

    Args:
        session: 数据库会话依赖。
        request: 包含邮箱和密码的请求体。

    Returns:
        UserPublic: 更新后的用户信息。

    Raises:
        HTTPException: 邮箱或密码错误（400）；用户未激活（400）；已同意过隐私协议（400）。
    """
    user = crud.authenticate(session=session, email=request.email, password=request.password)
    if not user:
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")

    if user.privacy_policy_accepted:
        raise HTTPException(status_code=400, detail="您已同意过隐私协议")

    user.privacy_policy_accepted = True
    user.privacy_policy_accepted_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@router.get("/status", response_model=dict)
def check_privacy_policy_status(*, current_user: CurrentUser) -> Any:
    """检查当前用户的隐私协议同意状态。

    Args:
        current_user: 当前登录用户。

    Returns:
        dict: 包含同意状态和同意时间的字典。
    """
    return {
        "accepted": current_user.privacy_policy_accepted,
        "accepted_at": current_user.privacy_policy_accepted_at.isoformat()
        if current_user.privacy_policy_accepted_at
        else None,
    }

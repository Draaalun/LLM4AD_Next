"""
通用工具路由。

提供健康检查和邮件测试等基础工具端点。
"""

from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser
from app.models import Message
from app.utils.email import generate_test_email, send_email

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """发送测试邮件（仅超级管理员可用）。

    用于验证邮件服务的可达性与模板渲染是否正常。

    Args:
        email_to: 测试邮件收件人地址。

    Returns:
        Message: 发送结果提示。
    """
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="测试邮件已发送")


@router.get("/health-check/")
async def health_check() -> bool:
    """健康检查端点。

    供监控/负载均衡探活使用，固定返回 ``True`` 表示服务在线。

    Returns:
        bool: 始终为 ``True``。
    """
    return True

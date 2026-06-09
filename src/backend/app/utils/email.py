"""
邮件服务模块。

提供邮件发送、邮件模板渲染、密码重置令牌生成与验证等功能。
支持 SMTP/TLS/SSL 多种邮件发送方式。
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import emails  # type: ignore
import jwt
from jinja2 import Template
from jwt.exceptions import InvalidTokenError

from app.core import security
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    """邮件数据，包含 HTML 正文和邮件主题。"""

    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    """渲染邮件 HTML 模板。

    Args:
        template_name: 模板文件名，相对于 email-templates/html/ 目录
        context: Jinja2 模板渲染上下文变量

    Returns:
        渲染后的 HTML 字符串
    """
    template_str = (
        Path(__file__).parent.parent / "email-templates" / "html" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    logger.info(f'email context: {context}')
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> None:
    """发送邮件。

    根据配置自动选择 TLS 或 SSL 加密方式。

    Args:
        email_to: 收件人邮箱
        subject: 邮件主题
        html_content: HTML 正文内容
    """
    assert settings.emails_enabled, "邮件服务未配置"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {"host": settings.SMTP_HOST, "port": settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"邮件发送结果: {response}")


def generate_test_email(email_to: str) -> EmailData:
    """生成测试邮件内容。"""
    project_name = settings.PROJECT_NAME.upper()
    subject = f"{project_name} - 测试邮件"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME.upper(), "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, email: str, token: str) -> EmailData:
    """生成密码重置邮件内容，包含重置链接。"""
    project_name = settings.PROJECT_NAME.upper()
    subject = f"{project_name} - 用户 {email} 的密码找回"
    link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"
    html_content = render_email_template(
        template_name="reset_password.html",
        context={
            "project_name": settings.PROJECT_NAME.upper(),
            "username": email,
            "email": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    """生成新账号欢迎邮件内容。"""
    project_name = settings.PROJECT_NAME.upper()
    subject = f"{project_name} - 用户 {username} 的新账号"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME.upper(),
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.FRONTEND_HOST,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_verify_code() -> str:
    """Generate a random 6-digit verification code."""
    import random

    return f"{random.randint(0, 999999):06d}"


def generate_verify_email(email_to: str, code: str) -> EmailData:
    """Generate an email with a 6-digit verification code."""
    project_name = settings.PROJECT_NAME.upper()
    subject = f"{project_name} - 邮箱验证码"
    html_content = render_email_template(
        template_name="verify_email.html",
        context={
            "project_name": project_name,
            "email": email_to,
            "code": code,
            "valid_minutes": settings.EMAIL_VERIFY_CODE_EXPIRE_MINUTES,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_password_reset_token(email: str) -> str:
    """生成密码重置 JWT 令牌。

    Args:
        email: 用户邮箱，作为令牌的 subject

    Returns:
        编码后的 JWT 字符串
    """
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(UTC)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    """验证密码重置令牌并提取邮箱。

    Returns:
        验证成功返回邮箱字符串，失败返回 None
    """
    try:
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None

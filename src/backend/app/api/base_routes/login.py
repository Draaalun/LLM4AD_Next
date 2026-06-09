"""
用户认证路由。

提供登录、令牌刷新、密码找回和重置等端点。
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.core.security import decode_access_token
from app.crud import user as crud
from app.models import Message, NewPassword, Token, User, UserUpdate
from app.utils.email import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


@router.post("/login/access-token", summary="根据邮箱账号密码登录")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """使用邮箱和密码登录，返回访问令牌和刷新令牌。

    采用 OAuth2 密码模式表单提交（form_data.username 即为邮箱）。
    校验账号密码并确认账号已激活后，签发两类 JWT 令牌。

    Args:
        session: 数据库会话依赖。
        form_data: OAuth2 密码模式表单，包含 username（邮箱）与 password。

    Returns:
        Token: 包含 access_token 与 refresh_token 的响应对象。

    Raises:
        HTTPException: 邮箱或密码错误（400）；用户未激活（400）。
    """
    user = crud.authenticate(session=session, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="邮箱或密码错误")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    elif not user.email_verified:
        raise HTTPException(status_code=409, detail="邮箱未验证，请先完成邮箱验证")
    elif not user.privacy_policy_accepted:
        raise HTTPException(status_code=403, detail="请先同意隐私协议")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(user.id, expires_delta=access_token_expires),
        refresh_token=security.create_access_token(user.id, expires_delta=refresh_token_expires, scope="refresh"),
    )


class RefreshAccessToken(BaseModel):
    """刷新令牌请求体。"""

    refresh_token: str


@router.post("/login/refresh-token", summary="刷新token")
def refresh_access_token(session: SessionDep, body: RefreshAccessToken) -> Token:
    """使用刷新令牌获取新的访问令牌和刷新令牌。

    校验 refresh scope 的 JWT 有效性，并确认用户存在且处于激活状态后，
    重新签发一对新的 access/refresh 令牌（滚动刷新策略）。

    Args:
        session: 数据库会话依赖。
        body: 刷新令牌请求体，包含 refresh_token 字段。

    Returns:
        Token: 新的 access_token 与 refresh_token。

    Raises:
        HTTPException: 令牌无效（401）；用户不存在或未启用（401）。
    """
    payload = decode_access_token(token=body.refresh_token, scope="refresh")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token无效！")

    user = session.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或未启用！")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(user.id, expires_delta=access_token_expires),
        refresh_token=security.create_access_token(user.id, expires_delta=refresh_token_expires, scope="refresh"),
    )


@router.post("/password-recovery/{email}", summary="找回密码申请")
def recover_password(email: str, session: SessionDep) -> Message:
    """发起密码找回流程，向用户邮箱发送重置链接。

    生成一次性密码重置令牌，并通过邮件下发给用户。

    Args:
        email: 待找回密码的账号邮箱。
        session: 数据库会话依赖。

    Returns:
        Message: 操作结果提示。

    Raises:
        HTTPException: 用户不存在（404）。
    """
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(email_to=user.email, email=email, token=password_reset_token)
    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="密码找回邮件已发送，请根据邮件提示进行重置密码！")


@router.post("/reset-password/", summary="重置密码")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """使用重置令牌设置新密码。

    校验邮件中携带的一次性令牌，确认用户存在且激活后，重写其密码哈希。

    Args:
        session: 数据库会话依赖。
        body: 包含 token 与 new_password 的请求体。

    Returns:
        Message: 操作结果提示。

    Raises:
        HTTPException: 令牌无效或用户不存在（400）；用户未激活（400）。
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="无效的令牌")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(status_code=400, detail="无效的令牌")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(session=session, db_user=user, user_in=user_in_update)
    return Message(message="密码重置成功")

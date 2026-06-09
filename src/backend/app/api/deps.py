"""
依赖注入模块。

定义 FastAPI 的依赖注入组件，包括：
- 数据库会话（SessionDep）
- OAuth2 令牌解析（TokenDep）
- 当前用户获取（CurrentUser）
- 超级管理员校验（CurrentActiveSuperuserUser）
- 特定权限校验（require_permission）
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.core.security import decode_access_token
from app.models import User

# OAuth2 密码模式令牌获取端点
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token")
# OAuth2 可选令牌（支持匿名访问）
optional_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """提供 FastAPI 路由使用的数据库会话。

    使用上下文管理器保证请求结束后自动关闭会话，避免连接泄漏。

    Yields:
        Session: SQLModel 数据库会话。
    """
    with Session(engine) as session:
        yield session


# 类型别名：数据库会话依赖
SessionDep = Annotated[Session, Depends(get_db)]
# 类型别名：OAuth2 令牌依赖
TokenDep = Annotated[str, Depends(reusable_oauth2)]
# 类型别名：可选 OAuth2 令牌依赖
OptionalTokenDep = Annotated[str | None, Depends(optional_oauth2)]


def get_current_user(session: SessionDep, token: TokenDep) -> User:
    """解析令牌并获取当前登录用户。

    依次校验 JWT 有效性、用户是否存在、用户是否激活。

    Args:
        session: 数据库会话依赖。
        token: 由 ``OAuth2PasswordBearer`` 提取的访问令牌。

    Returns:
        User: 当前登录用户实体。

    Raises:
        HTTPException: 令牌无效（401）、用户不存在（401）或用户未激活（403）。
    """
    payload = decode_access_token(token=token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="当前无权限访问！")
    user = session.get(User, payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在！")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户尚未激活，请联系管理员激活！",
        )
    return user


def get_optional_user(session: SessionDep, token: OptionalTokenDep) -> User | None:
    """解析令牌并获取当前登录用户（可选）。

    支持匿名访问，如果没有提供 token 或 token 无效则返回 None。

    Args:
        session: 数据库会话依赖。
        token: 可选的 OAuth2 令牌。

    Returns:
        User | None: 当前登录用户，如果未登录或 token 无效则返回 None。
    """
    if not token:
        return None

    payload = decode_access_token(token=token)
    if not payload:
        return None

    user = session.get(User, payload["sub"])
    if not user or not user.is_active:
        return None

    return user


# 权限级别1：必须登录且用户有效
require_user = Depends(get_current_user)
CurrentUser = Annotated[User, require_user]

# 权限级别0：可选登录（支持匿名访问）
optional_user = Depends(get_optional_user)
OptionalUser = Annotated[User | None, optional_user]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    """校验当前用户是否为超级管理员。

    Args:
        current_user: 由 ``get_current_user`` 注入的当前登录用户。

    Returns:
        User: 当前登录的超级管理员。

    Raises:
        HTTPException: 当前用户非超级管理员（403）。
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="当前无权限操作，仅超级管理员可操作！")
    return current_user


# 权限级别2：必须为超级管理员
require_superuser = Depends(get_current_active_superuser)
CurrentActiveSuperuserUser = Annotated[User, require_superuser]


# 权限级别3：必须拥有指定权限（超级管理员自动通过）
def require_permission(permission_name: str):
    """创建特定权限的依赖注入。

    超级管理员自动通过；其他用户需通过其角色绑定的权限列表中匹配到目标权限。

    用法::

        @router.get("/xxx", dependencies=[require_permission("item:read")])

    Args:
        permission_name: 所需权限名称，格式为 "资源:操作"。

    Returns:
        Depends: 可放入 FastAPI ``dependencies`` 列表的依赖对象。
    """

    async def _permission_dependency(current_user: CurrentUser):
        # 超级管理员直接通过
        if current_user.is_superuser:
            return True
        # 遍历用户角色下的权限列表
        for role in current_user.roles:
            for perm in role.permissions:
                if perm.name == permission_name:
                    return True
        raise HTTPException(status_code=403, detail=f"当前无权限操作 {permission_name}！")

    return Depends(_permission_dependency)

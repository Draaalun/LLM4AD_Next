"""
权限管理路由。

提供权限的创建、查询端点，仅超级管理员可操作。
"""

from fastapi import APIRouter

from app.api.deps import SessionDep, require_superuser
from app.crud.permission import PermissionCRUD
from app.models import Permission, PermissionBase

router = APIRouter(prefix="/permission", tags=["permission"])


@router.post("create", dependencies=[require_superuser])
def create(body: PermissionBase, session: SessionDep):
    """创建新权限（仅超级管理员）。

    Args:
        body: 权限创建请求体，包含权限名称等字段。
        session: 数据库会话依赖。

    Returns:
        Permission: 创建后的权限对象。
    """
    crud = PermissionCRUD(Permission, session)
    db_obj = crud.create(body)
    return db_obj


@router.get("get", dependencies=[require_superuser])
def get(pk, session: SessionDep):
    """根据主键获取单个权限（仅超级管理员）。

    Args:
        pk: 权限主键。
        session: 数据库会话依赖。

    Returns:
        Permission | None: 命中的权限对象，未找到时为 ``None``。
    """
    crud = PermissionCRUD(Permission, session)
    db_obj = crud.get(pk)
    return db_obj


@router.get("permissions", dependencies=[require_superuser])
def permissions(session: SessionDep):
    """获取所有权限列表（仅超级管理员）。

    Args:
        session: 数据库会话依赖。

    Returns:
        list[Permission]: 全量权限列表。
    """
    crud = PermissionCRUD(Permission, session)
    db_obj = crud.get_multi()
    return db_obj

"""
RBAC 权限模型。

定义角色（Role）、权限（Permission）以及关联表，
实现基于角色的访问控制（Role-Based Access Control）。
"""

import uuid

from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TimeMixin

# ---- 关联表 ----


class UserRoleLink(SQLModel, table=True):
    """用户-角色多对多关联表。"""

    # 关联 ID 允许为空，不关联任何用户或角色
    user_id: uuid.UUID | None = Field(None, foreign_key="user.id", primary_key=True)
    role_id: uuid.UUID | None = Field(None, foreign_key="role.id", primary_key=True)


class RolePermissionLink(SQLModel, table=True):
    """角色-权限多对多关联表。"""

    # 关联 ID 允许为空，不关联任何角色或权限
    role_id: uuid.UUID | None = Field(None, foreign_key="role.id", primary_key=True)
    permission_id: uuid.UUID | None = Field(None, foreign_key="permission.id", primary_key=True)


# ---- 角色 ----


class RoleBase(SQLModel):
    """角色基础 Schema，定义角色的公共字段。"""

    name: str = Field("", max_length=255)
    description: str = Field("", max_length=255)


class Role(RoleBase, TimeMixin, table=True):
    """角色数据库模型。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    users: list["User"] = Relationship(back_populates="roles", link_model=UserRoleLink)  # type: ignore[name-defined]  # noqa: F821
    permissions: list["Permission"] = Relationship(back_populates="roles", link_model=RolePermissionLink)


# ---- 权限 ----


class PermissionBase(SQLModel):
    """权限基础 Schema，定义权限的公共字段。"""

    name: str = Field("", max_length=255)
    description: str = Field("", max_length=255)
    type: str = Field("", max_length=255, description="权限类型，备用")


class Permission(PermissionBase, TimeMixin, table=True):
    """权限数据库模型。"""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    roles: list["Role"] = Relationship(back_populates="permissions", link_model=RolePermissionLink)

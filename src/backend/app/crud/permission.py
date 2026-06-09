"""
权限数据访问模块。

继承通用 CRUD 基类，提供权限模型的标准增删改查操作。
"""

from app.crud.base import BaseCRUD
from app.models import Permission, PermissionBase


class PermissionCRUD(BaseCRUD[Permission, PermissionBase, PermissionBase]):
    """权限 CRUD 操作类，使用 PermissionBase 作为创建和更新的 Schema。"""

    pass

"""
用户数据访问模块。

提供用户的创建、更新、查询、认证等数据库操作函数。
包含防时序攻击的认证逻辑和密码哈希自动升级机制。
"""

import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, User, UserCreate, UserDefaultModel, UserUpdate


def create_user(*, session: Session, user_create: UserCreate) -> User:
    """创建新用户，自动将明文密码转为哈希存储，并同步初始化默认模型配置。"""
    # 延迟导入避免 crud ↔ services 任何潜在的循环
    from app.services.user_default_model_service import build_default_init_kwargs

    db_obj = User.model_validate(user_create, update={"hashed_password": get_password_hash(user_create.password)})
    session.add(db_obj)
    session.flush()  # 拿主键但不提交，与下面的 UserDefaultModel 同事务

    init_kwargs = build_default_init_kwargs(session, db_obj.id)
    session.add(UserDefaultModel(**init_kwargs))

    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    """更新用户信息，若包含密码字段则自动重新哈希。"""
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def update_superuser(*, session: Session, db_user: User, user_in: UserUpdate):
    """更新超级管理员信息，自动设置激活和超管标志。"""
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {"is_active": True, "is_superuser": True}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
        extra_data["is_active"] = True
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    """根据邮箱查询用户。"""
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


# 用于防时序攻击的虚拟哈希值
# 当用户不存在时仍执行密码验证，确保响应时间一致，防止通过响应时间推断邮箱是否存在
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    """验证用户邮箱和密码，支持密码哈希自动升级。

    采用恒定时间比较策略：即使用户不存在也执行密码验证，
    防止通过响应时间差异推断邮箱是否注册。
    """
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        # 用户不存在时仍执行验证以防止时序攻击
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    # 若密码哈希算法已升级，自动更新存储的哈希值
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    """创建条目，关联到指定用户。"""
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

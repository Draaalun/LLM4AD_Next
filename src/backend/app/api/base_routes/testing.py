"""
测试与调试路由。

提供权限验证、S3 连接、Celery 任务等测试端点。
注意：使用 /utils 前缀以保持 API URL 向后兼容。
"""

from fastapi import APIRouter
from loguru import logger

from app.api.deps import (
    CurrentActiveSuperuserUser,
    CurrentUser,
    require_permission,
    require_superuser,
    require_user,
)
from app.core.celery import celery_app
from app.core.storage import storage
from app.models import Message

router = APIRouter(prefix="/utils", tags=["utils.testing"])


# ---- S3 存储测试 ----

@router.get("/test_s3")
def test_s3(current_user: CurrentUser) -> Message:  # noqa: ARG001
    """测试 S3/RustFS 存储服务是否正常。

    通过尝试创建/确认 ``test-bucket`` 存在来验证存储服务连通性。
    需要登录用户身份（依赖 ``current_user`` 触发鉴权，函数体内不使用）。

    Args:
        current_user: 当前登录用户依赖，仅用于强制鉴权。

    Returns:
        Message: 测试结果提示。
    """
    storage.ensure_bucket("test-bucket")
    return Message(message="成功")


# ---- 权限验证测试 ----

@router.get("/test_current_user_dp", dependencies=[require_user], summary="测试当前用户依赖")
def test_current_user_dp():
    """测试 require_user 依赖注入是否正常工作。"""
    return Message()


@router.get("/test_current_user", summary="测试当前用户")
def test_current_user(current_user: CurrentUser):
    """测试获取当前登录用户信息。"""
    return current_user


@router.get("/test_superuser_dp", dependencies=[require_superuser], summary="测试需要超管权限依赖")
def test_superuser_dp():
    """测试 require_superuser 依赖注入是否正常工作。"""
    return Message()


@router.get("/test_superuser", summary="测试需要超管权限")
def test_superuser(current_user: CurrentActiveSuperuserUser):
    """测试获取超级管理员用户信息。"""
    return current_user


@router.get(
    "/test_require_permission_dp",
    dependencies=[require_permission("item:read")],
    summary="测试需要特定权限依赖（超管除外）",
)
def test_require_permission_dp():
    """测试 require_permission 依赖注入（需 item:read 权限）。"""
    return Message()


# ---- Celery 任务测试 ----

@router.get("/test_get_task_info", summary="测试获取任务信息")
async def test_get_task_info(task_id: str):
    """测试查询 Celery 任务状态（注意：Celery 永远能返回结果，需自行维护任务表）。"""
    celery_task = celery_app.AsyncResult(task_id)
    logger.info(celery_task.state)
    logger.info(celery_task.successful())
    return Message()

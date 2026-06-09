"""
微信群活码管理路由（管理端，仅超级管理员）。

提供活码与真实群码的增删改查、永久二维码下载、群码图片预览等端点。
活码是一项面向运营的管理能力，仅超级管理员可访问，且所有管理员共享同一份活码池
（可管理彼此创建的活码，``user_id`` 仅记录创建者）。鉴权在路由层统一拦截：整个路由
通过 ``dependencies=[require_superuser]`` 要求超级管理员，service 层不再关心调用者身份。
面向终端用户的扫码落地页见 ``live_qr`` 路由，无需鉴权。
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from app.api.deps import CurrentActiveSuperuserUser, SessionDep, require_superuser
from app.models import Message
from app.schemas import live_code as schemas
from app.services import live_code_service as service

# 整个管理路由仅超级管理员可访问
router = APIRouter(prefix="/live-codes", tags=["live-codes"], dependencies=[require_superuser])


def _base_override(request: Request) -> str:
    """从请求推导对外基础 URL，作为未显式配置 FRONTEND_HOST 时的回退。"""
    return str(request.base_url).rstrip("/")


# ---- 活码 ----


@router.post("/", response_model=schemas.LiveCodeDetail, status_code=201, summary="创建活码")
def create_live_code(
    live_code_in: schemas.LiveCodeCreate,
    db: SessionDep,
    current_user: CurrentActiveSuperuserUser,
    request: Request,
):
    """创建一个活码，自动生成永久短码并记录创建者。"""
    live_code = service.create_live_code(db, live_code_in, current_user.id)
    creator = service.creators_for(db, [live_code]).get(live_code.user_id) if live_code.user_id else None
    return service.to_live_code_detail(live_code, _base_override(request), datetime.now(UTC), creator)


@router.get("/", response_model=schemas.PaginatedLiveCode, summary="分页查询活码列表")
def list_live_codes(
    db: SessionDep,
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """分页查询全部活码（全管理员共享）。"""
    items, total = service.list_live_codes(db, skip, limit)
    base = _base_override(request)
    now = datetime.now(UTC)
    creators = service.creators_for(db, items)
    return schemas.PaginatedLiveCode(
        items=[
            service.to_live_code_public(item, base, now, creators.get(item.user_id))
            for item in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{live_code_id}", response_model=schemas.LiveCodeDetail, summary="获取活码详情")
def get_live_code(live_code_id: uuid.UUID, db: SessionDep, request: Request):
    """获取活码详情，包含全部真实群码及其实时有效状态。"""
    live_code = service.get_live_code_or_404(db, live_code_id)
    creator = service.creators_for(db, [live_code]).get(live_code.user_id) if live_code.user_id else None
    return service.to_live_code_detail(live_code, _base_override(request), datetime.now(UTC), creator)


@router.patch("/{live_code_id}", response_model=schemas.LiveCodeDetail, summary="更新活码")
def update_live_code(
    live_code_id: uuid.UUID,
    live_code_update: schemas.LiveCodeUpdate,
    db: SessionDep,
    request: Request,
):
    """更新活码名称、切换策略、落地页文案、启用状态等。"""
    live_code = service.update_live_code(db, live_code_id, live_code_update)
    creator = service.creators_for(db, [live_code]).get(live_code.user_id) if live_code.user_id else None
    return service.to_live_code_detail(live_code, _base_override(request), datetime.now(UTC), creator)


@router.delete("/{live_code_id}", response_model=Message, summary="删除活码")
def delete_live_code(live_code_id: uuid.UUID, db: SessionDep):
    """删除活码及其全部真实群码（含对象存储清理）。"""
    return service.delete_live_code(db, live_code_id)


# ---- 真实群码 ----


@router.post(
    "/{live_code_id}/targets",
    response_model=schemas.LiveCodeDetail,
    status_code=201,
    summary="批量上传真实群码",
)
def add_targets(
    live_code_id: uuid.UUID,
    db: SessionDep,
    request: Request,
    files: list[UploadFile] = File(..., description="真实群码图片，可多张"),
    valid_days: int = Form(
        service.DEFAULT_TARGET_VALID_DAYS, description="有效天数，<=0 表示永不过期，默认 7"
    ),
    scan_limit: int | None = Form(None, description="扫码次数上限（近似人数），留空表示不限"),
):
    """为活码批量上传真实群码图片，统一设置有效期与扫码上限。"""
    service.add_targets(db, live_code_id, files, valid_days, scan_limit)
    live_code = service.get_live_code_or_404(db, live_code_id)
    return service.to_live_code_detail(live_code, _base_override(request), datetime.now(UTC))


@router.patch(
    "/{live_code_id}/targets/{target_id}",
    response_model=schemas.TargetPublic,
    summary="更新真实群码",
)
def update_target(
    live_code_id: uuid.UUID,
    target_id: uuid.UUID,
    target_update: schemas.TargetUpdate,
    db: SessionDep,
):
    """更新真实群码的备注、过期时间、扫码上限、启用状态、排序。"""
    target = service.update_target(db, live_code_id, target_id, target_update)
    return service.to_target_public(target, datetime.now(UTC))


@router.post(
    "/{live_code_id}/targets/{target_id}/reset-scan",
    response_model=schemas.TargetPublic,
    summary="重置真实群码扫码计数",
)
def reset_target_scan(live_code_id: uuid.UUID, target_id: uuid.UUID, db: SessionDep):
    """将某张真实群码的扫码计数清零，便于满员后复用同一张群码。"""
    target = service.reset_target_scans(db, live_code_id, target_id)
    return service.to_target_public(target, datetime.now(UTC))


@router.delete(
    "/{live_code_id}/targets/{target_id}",
    response_model=Message,
    summary="删除真实群码",
)
def delete_target(live_code_id: uuid.UUID, target_id: uuid.UUID, db: SessionDep):
    """删除某张真实群码（含对象存储清理）。"""
    return service.delete_target(db, live_code_id, target_id)

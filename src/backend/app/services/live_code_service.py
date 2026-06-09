"""
微信群活码服务层。

封装活码（LiveCode）与真实群码（LiveCodeTarget）的全部业务逻辑：

- 活码与真实群码的增删改查、权限校验；
- 真实群码图片的对象存储读写；
- 扫码时按切换策略动态选码、扫码计数；
- 永久二维码 PNG 生成；
- 公开落地页 HTML 渲染。

路由层只做参数解析与依赖注入，业务一律下沉到本模块，保持关注点分离。
"""

import html
import io
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, UploadFile
from loguru import logger
from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.storage import storage
from app.models import (
    ContactDisplay,
    LiveCode,
    LiveCodeStrategy,
    LiveCodeTarget,
    Message,
    User,
)
from app.schemas import live_code as schemas

# 单张真实群码图片大小上限（MB）
_MAX_IMAGE_SIZE_MB = 10
# 允许上传的图片 MIME 类型
_ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
# 真实群码默认有效期（天），对齐微信群二维码 7 天有效期
DEFAULT_TARGET_VALID_DAYS = 7


# ---- URL / 路径构造 ----


def resolve_public_base(base_override: str | None = None) -> str:
    """解析对外可达的基础 URL（不含末尾斜杠）。

    优先级：显式入参 > ``settings.FRONTEND_HOST`` > 空串（由调用方回退到请求推导）。

    Args:
        base_override: 调用方传入的基础 URL（通常由请求 ``base_url`` 推导）。

    Returns:
        规范化后的基础 URL，可能为空字符串。
    """
    base = settings.FRONTEND_HOST or (base_override or "")
    return base.rstrip("/")


def build_public_url(slug: str, base_override: str | None = None) -> str:
    """构造活码对外永久落地页 URL（即永久二维码所编码的内容）。"""
    base = resolve_public_base(base_override)
    return f"{base}{settings.API_V1_STR}/live-qr/{slug}"


def build_scan_image_url(slug: str, base_override: str | None = None) -> str:
    """构造落地页内嵌的实时群码图片 URL。"""
    base = resolve_public_base(base_override)
    return f"{base}{settings.API_V1_STR}/live-qr/{slug}/image"


def build_qrcode_path(slug: str) -> str:
    """构造永久二维码 PNG 的公开相对路径（免鉴权，可直接用于 ``<img>`` / 下载）。"""
    return f"{settings.API_V1_STR}/live-qr/{slug}/qrcode"


def build_target_image_path(target_id: uuid.UUID) -> str:
    """构造真实群码图片的公开相对路径（免鉴权，可直接用于 ``<img>``）。"""
    return f"{settings.API_V1_STR}/live-qr/targets/{target_id}/image"


# ---- 查询辅助 ----


def get_live_code_or_404(db: Session, live_code_id: uuid.UUID) -> LiveCode:
    """按 ID 获取活码，不存在则抛 404。

    访问控制（仅超级管理员）由路由层统一拦截；活码是全管理员共享的运营资源，
    任一管理员均可读写任意活码，``user_id`` 仅用于记录创建者。

    Args:
        db: 数据库会话。
        live_code_id: 活码 ID。

    Returns:
        活码对象。

    Raises:
        HTTPException: 活码不存在（404）。
    """
    live_code = db.get(LiveCode, live_code_id)
    if not live_code:
        raise HTTPException(status_code=404, detail="活码不存在")
    return live_code


def get_live_code_by_slug(db: Session, slug: str) -> LiveCode | None:
    """按公开短码获取活码（公开端使用，不鉴权）。"""
    return db.exec(select(LiveCode).where(LiveCode.slug == slug)).first()


def list_contact_live_codes(db: Session) -> list[LiveCode]:
    """获取全部『联系我们』对外展示的活码（展示模式非 none 且已启用）。

    支持同时展示多张联系二维码，按创建时间正序排列，保证前端展示顺序稳定。
    """
    return list(
        db.exec(
            select(LiveCode)
            .where(
                LiveCode.contact_display != ContactDisplay.NONE,
                LiveCode.is_active.is_(True),  # type: ignore[attr-defined]
            )
            .order_by(LiveCode.created_time)
        ).all()
    )


def _generate_unique_slug(db: Session) -> str:
    """生成全局唯一的公开短码。"""
    for _ in range(10):
        slug = secrets.token_urlsafe(6)
        if not db.exec(select(LiveCode.id).where(LiveCode.slug == slug)).first():
            return slug
    # 极小概率连续冲突，退化为更长的随机串
    return secrets.token_urlsafe(12)


# ---- 活码 CRUD ----


def create_live_code(db: Session, data: schemas.LiveCodeCreate, user_id: uuid.UUID) -> LiveCode:
    """创建活码。"""
    live_code = LiveCode(
        slug=_generate_unique_slug(db),
        user_id=user_id,
        name=data.name,
        description=data.description,
        strategy=data.strategy,
        landing_title=data.landing_title,
        landing_tip=data.landing_tip,
    )
    db.add(live_code)
    db.commit()
    db.refresh(live_code)
    return live_code


def list_live_codes(db: Session, skip: int, limit: int) -> tuple[list[LiveCode], int]:
    """分页查询活码列表。

    返回全部活码（全管理员共享），按创建时间倒序。
    """
    total = db.exec(select(func.count()).select_from(LiveCode)).one()
    query = select(LiveCode).order_by(LiveCode.created_time.desc()).offset(skip).limit(limit)
    items = list(db.exec(query).all())
    return items, total


def update_live_code(
    db: Session, live_code_id: uuid.UUID, data: schemas.LiveCodeUpdate
) -> LiveCode:
    """更新活码基础信息。"""
    live_code = get_live_code_or_404(db, live_code_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(live_code, key, value)
    live_code.updated_time = datetime.now(UTC)
    db.add(live_code)
    db.commit()
    db.refresh(live_code)
    return live_code


def delete_live_code(db: Session, live_code_id: uuid.UUID) -> Message:
    """删除活码及其全部真实群码（含对象存储清理）。"""
    live_code = get_live_code_or_404(db, live_code_id)

    # 清理对象存储中该活码前缀下的所有图片
    try:
        keys = storage.list_objects(prefix=f"live_codes/{live_code_id}/")
        storage.delete_many(keys)
    except Exception:
        logger.exception("删除活码 {} 的对象存储文件失败", live_code_id)

    db.delete(live_code)  # 真实群码经 ondelete=CASCADE 自动删除
    db.commit()
    return Message(message="活码已删除")


# ---- 真实群码 CRUD ----


def _validate_image(file: UploadFile, content: bytes) -> str:
    """校验上传图片的类型与大小，返回归一化的文件扩展名。

    Raises:
        HTTPException: 类型不支持（400）或超过大小上限（400）。
    """
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片类型：{file.content_type}，仅支持 PNG/JPEG/WebP/GIF",
        )
    if len(content) > _MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"单张图片不能超过 {_MAX_IMAGE_SIZE_MB}MB")
    if not content:
        raise HTTPException(status_code=400, detail="上传的图片内容为空")
    return _ALLOWED_IMAGE_TYPES[content_type]


def add_targets(
    db: Session,
    live_code_id: uuid.UUID,
    files: list[UploadFile],
    valid_days: int | None = DEFAULT_TARGET_VALID_DAYS,
    scan_limit: int | None = None,
) -> list[LiveCodeTarget]:
    """为活码批量添加真实群码。

    Args:
        db: 数据库会话。
        live_code_id: 活码 ID。
        files: 上传的群码图片列表。
        valid_days: 有效天数；<=0 或 None 表示永不过期，默认 7 天。
        scan_limit: 扫码次数上限；None 表示不限。

    Returns:
        新建的真实群码列表。
    """
    live_code = get_live_code_or_404(db, live_code_id)

    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张群码图片")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="单次最多上传 50 张")

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=valid_days) if valid_days and valid_days > 0 else None
    # 追加到现有群码之后
    base_sort = max((t.sort_order for t in live_code.targets), default=-1) + 1

    created: list[LiveCodeTarget] = []
    for idx, file in enumerate(files):
        content = file.file.read()
        ext = _validate_image(file, content)
        target_id = uuid.uuid4()
        key = f"live_codes/{live_code_id}/targets/{target_id}{ext}"
        storage.upload(key, content, content_type=file.content_type)
        target = LiveCodeTarget(
            id=target_id,
            live_code_id=live_code_id,
            image_key=key,
            content_type=file.content_type or "image/png",
            original_filename=file.filename,
            expires_at=expires_at,
            scan_limit=scan_limit,
            sort_order=base_sort + idx,
        )
        db.add(target)
        created.append(target)

    db.commit()
    for target in created:
        db.refresh(target)
    return created


def _get_target_or_404(
    db: Session, live_code_id: uuid.UUID, target_id: uuid.UUID
) -> LiveCodeTarget:
    """获取真实群码并校验其归属于指定活码，否则抛 404。"""
    get_live_code_or_404(db, live_code_id)
    target = db.get(LiveCodeTarget, target_id)
    if not target or target.live_code_id != live_code_id:
        raise HTTPException(status_code=404, detail="群码不存在")
    return target


def update_target(
    db: Session,
    live_code_id: uuid.UUID,
    target_id: uuid.UUID,
    data: schemas.TargetUpdate,
) -> LiveCodeTarget:
    """更新真实群码的备注、过期时间、上限、启用状态、排序等。"""
    target = _get_target_or_404(db, live_code_id, target_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(target, key, value)
    target.updated_time = datetime.now(UTC)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def reset_target_scans(
    db: Session, live_code_id: uuid.UUID, target_id: uuid.UUID
) -> LiveCodeTarget:
    """重置某张真实群码的扫码计数（用于手动复用群码）。"""
    target = _get_target_or_404(db, live_code_id, target_id)
    target.scan_count = 0
    target.updated_time = datetime.now(UTC)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def delete_target(db: Session, live_code_id: uuid.UUID, target_id: uuid.UUID) -> Message:
    """删除某张真实群码（含对象存储清理）。"""
    target = _get_target_or_404(db, live_code_id, target_id)
    try:
        storage.delete(target.image_key)
    except Exception:
        logger.exception("删除群码图片 {} 失败", target.image_key)
    db.delete(target)
    db.commit()
    return Message(message="群码已删除")


def get_target_image_by_id(db: Session, target_id: uuid.UUID) -> tuple[bytes, str] | None:
    """按 target_id 返回真实群码图片字节与 MIME 类型（公开端使用，不鉴权）。

    群码图片本就是供终端用户扫码的公开内容；按不可枚举的 UUID 直取，找不到或
    图片缺失时返回 None。
    """
    target = db.get(LiveCodeTarget, target_id)
    if not target:
        return None
    try:
        data = storage.download(target.image_key)
    except Exception:
        logger.exception("下载群码图片 {} 失败", target.image_key)
        return None
    return data, target.content_type


# ---- 有效性判定与选码 ----


def target_status(target: LiveCodeTarget, now: datetime) -> str:
    """计算真实群码的人类可读状态。

    Returns:
        ``valid`` / ``disabled`` / ``expired`` / ``full`` 之一。
    """
    if not target.is_enabled:
        return "disabled"
    if target.expires_at and target.expires_at <= now:
        return "expired"
    if target.scan_limit is not None and target.scan_count >= target.scan_limit:
        return "full"
    return "valid"


def select_valid_targets(live_code: LiveCode, now: datetime) -> list[LiveCodeTarget]:
    """筛选出当前有效的真实群码，按 ``sort_order`` 升序排列。"""
    valid = [t for t in live_code.targets if target_status(t, now) == "valid"]
    valid.sort(key=lambda t: (t.sort_order, t.created_time))
    return valid


def pick_target(live_code: LiveCode, now: datetime) -> LiveCodeTarget | None:
    """按活码配置的切换策略挑选一张有效真实群码。

    轮询策略会就地推进 ``live_code.rotation_cursor``（由调用方统一提交）。

    Returns:
        选中的真实群码；无有效群码时返回 None。
    """
    valid = select_valid_targets(live_code, now)
    if not valid:
        return None

    if live_code.strategy == LiveCodeStrategy.RANDOM:
        return secrets.choice(valid)
    if live_code.strategy == LiveCodeStrategy.ROUND_ROBIN:
        index = live_code.rotation_cursor % len(valid)
        live_code.rotation_cursor = (live_code.rotation_cursor + 1) % (10**9)
        return valid[index]
    # 默认顺延：始终取序号最小的有效群码
    return valid[0]


def serve_scan(db: Session, slug: str, count: bool = True) -> tuple[bytes, str] | None:
    """公开扫码：选出当前有效群码并返回其图片字节，可选地累计扫码计数。

    Args:
        db: 数据库会话。
        slug: 活码公开短码。
        count: 是否累计扫码计数。重复扫码去重由调用方（路由）通过 cookie 判定，
            已计过的同一客户端传 ``False`` 避免重复 +1。

    Returns:
        ``(图片字节, MIME 类型)``；活码不存在/停用/无有效群码/图片缺失时返回 None。
    """
    live_code = get_live_code_by_slug(db, slug)
    if not live_code or not live_code.is_active:
        return None

    now = datetime.now(UTC)
    target = pick_target(live_code, now)
    if not target:
        return None

    # 累计扫码计数（近似人数，用于满员自动切换与统计）；轮询游标在 count=False 时
    # 也已被 pick_target 推进，需要持久化，故无论是否计数都提交。
    if count:
        target.scan_count += 1
        live_code.total_scans += 1
    db.add(target)
    db.add(live_code)
    db.commit()

    try:
        data = storage.download(target.image_key)
    except Exception:
        logger.exception("下载群码图片 {} 失败", target.image_key)
        return None
    return data, target.content_type


# ---- 永久二维码生成 ----


def generate_permanent_qr_png(data: str) -> bytes:
    """生成编码 ``data`` 的永久二维码 PNG 字节。

    Raises:
        HTTPException: 未安装 ``qrcode`` 依赖（500）。
    """
    try:
        import qrcode
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="二维码生成依赖未安装，请在后端执行 `uv sync` 安装 qrcode[pil]",
        )

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---- 响应组装 ----


def to_target_public(target: LiveCodeTarget, now: datetime) -> schemas.TargetPublic:
    """将真实群码 ORM 对象转换为响应模型。"""
    status = target_status(target, now)
    return schemas.TargetPublic(
        id=target.id,
        label=target.label,
        expires_at=target.expires_at,
        scan_limit=target.scan_limit,
        scan_count=target.scan_count,
        is_enabled=target.is_enabled,
        sort_order=target.sort_order,
        created_time=target.created_time,
        image_url=build_target_image_path(target.id),
        is_valid=status == "valid",
        status=status,
    )


def to_live_code_public(
    live_code: LiveCode,
    base_override: str | None,
    now: datetime,
    creator: User | None = None,
) -> schemas.LiveCodePublic:
    """将活码 ORM 对象转换为列表响应模型。"""
    targets = live_code.targets
    valid_count = sum(1 for t in targets if target_status(t, now) == "valid")
    return schemas.LiveCodePublic(
        id=live_code.id,
        slug=live_code.slug,
        name=live_code.name,
        description=live_code.description,
        strategy=live_code.strategy,
        landing_title=live_code.landing_title,
        landing_tip=live_code.landing_tip,
        is_active=live_code.is_active,
        contact_display=live_code.contact_display,
        total_scans=live_code.total_scans,
        created_time=live_code.created_time,
        updated_time=live_code.updated_time,
        public_url=build_public_url(live_code.slug, base_override),
        qrcode_url=build_qrcode_path(live_code.slug),
        target_count=len(targets),
        valid_target_count=valid_count,
        creator_email=creator.email if creator else None,
        creator_name=creator.full_name if creator else None,
    )


def creators_for(db: Session, live_codes: list[LiveCode]) -> dict[uuid.UUID, User]:
    """批量解析一批活码的创建者，返回 ``{user_id: User}`` 映射（避免 N+1 查询）。"""
    ids = {lc.user_id for lc in live_codes if lc.user_id}
    if not ids:
        return {}
    users = db.exec(select(User).where(User.id.in_(ids))).all()  # type: ignore[attr-defined]
    return {u.id: u for u in users}


def to_contact_info(live_code: LiveCode) -> schemas.LiveCodeContactInfo:
    """将联系活码转换为公开展示信息，按展示模式解析出最终图片 URL（相对路径）。

    - ``landing``：返回永久码 PNG 路径（编码落地页 URL，扫码后可轮换真实群码）；
    - ``direct``：返回第一张有效真实码的图片路径（适合永久码，无有效码时为空串）。

    统一返回相对 API 路径，由前端按需拼接 base，与 ``qrcode_url`` / 真实码图片一致。
    """
    if live_code.contact_display == ContactDisplay.DIRECT:
        valid = select_valid_targets(live_code, datetime.now(UTC))
        image_url = build_target_image_path(valid[0].id) if valid else ""
    else:
        image_url = build_qrcode_path(live_code.slug)

    return schemas.LiveCodeContactInfo(
        slug=live_code.slug,
        landing_title=live_code.landing_title,
        landing_tip=live_code.landing_tip,
        display=live_code.contact_display,
        image_url=image_url,
    )


def to_live_code_detail(
    live_code: LiveCode,
    base_override: str | None,
    now: datetime,
    creator: User | None = None,
) -> schemas.LiveCodeDetail:
    """将活码 ORM 对象转换为详情响应模型（含真实群码列表）。"""
    public = to_live_code_public(live_code, base_override, now, creator)
    sorted_targets = sorted(live_code.targets, key=lambda t: (t.sort_order, t.created_time))
    return schemas.LiveCodeDetail(
        **public.model_dump(),
        targets=[to_target_public(t, now) for t in sorted_targets],
    )


# ---- 公开落地页渲染 ----


def render_landing_page(db: Session, slug: str, base_override: str | None) -> tuple[str, int]:
    """渲染公开落地页 HTML。

    Returns:
        ``(html, status_code)``。
    """
    live_code = get_live_code_by_slug(db, slug)
    if not live_code:
        return _landing_html(title="链接无效", message="该二维码不存在或已被删除。", state="error"), 404
    if not live_code.is_active:
        return (
            _landing_html(
                title=live_code.landing_title or live_code.name,
                message="该群二维码已停用，请联系管理员。",
                state="inactive",
            ),
            200,
        )

    now = datetime.now(UTC)
    has_valid = bool(select_valid_targets(live_code, now))
    title = live_code.landing_title or live_code.name
    tip = live_code.landing_tip or "长按二维码，识别加入群聊"

    if not has_valid:
        return (
            _landing_html(
                title=title,
                message="群二维码维护中，请稍后刷新重试，或联系管理员。",
                state="maintenance",
            ),
            200,
        )

    image_url = build_scan_image_url(slug, base_override)
    return _landing_html(title=title, tip=tip, image_url=image_url, state="ok"), 200


def _landing_html(
    title: str,
    *,
    tip: str = "",
    message: str = "",
    image_url: str = "",
    state: str = "ok",
) -> str:
    """生成移动端友好的落地页 HTML 文档。

    所有用户可控文本均经过 HTML 转义，避免存储型 XSS。
    """
    safe_title = html.escape(title or "加入群聊")
    safe_tip = html.escape(tip)
    safe_message = html.escape(message)

    if state == "ok":
        body = f"""
        <div class="card">
          <h1>{safe_title}</h1>
          <div class="qr-wrap">
            <img id="qr" src="{html.escape(image_url, quote=True)}" alt="群二维码"
                 onerror="document.getElementById('fallback').style.display='block';this.style.display='none';" />
          </div>
          <p class="tip">{safe_tip}</p>
          <p id="fallback" class="muted" style="display:none">
            二维码加载失败或维护中，请稍后下拉刷新重试。
          </p>
        </div>
        """
    else:
        icon = "🛠️" if state == "maintenance" else "⚠️"
        body = f"""
        <div class="card">
          <div class="icon">{icon}</div>
          <h1>{safe_title}</h1>
          <p class="muted">{safe_message}</p>
          <button class="btn" onclick="location.reload()">刷新重试</button>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <meta name="referrer" content="no-referrer" />
  <title>{safe_title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
      background: linear-gradient(160deg, #07c160 0%, #10ad7a 100%); color: #1f2329; padding: 24px;
    }}
    .card {{
      background: #fff; border-radius: 20px; padding: 32px 24px; width: 100%; max-width: 360px;
      text-align: center; box-shadow: 0 12px 40px rgba(0,0,0,.18);
    }}
    h1 {{ font-size: 20px; margin: 0 0 20px; font-weight: 600; word-break: break-word; }}
    .qr-wrap {{
      width: 100%; padding:10px; text-align: center;
      display: block; overflow: hidden;
    }}
    .qr-wrap img {{ width: 100%; height: auto; display: inline-block; }}
    .tip {{ font-size: 15px; color: #07c160; margin: 0; font-weight: 500; }}
    .muted {{ font-size: 14px; color: #8a8f99; line-height: 1.6; margin: 12px 0 0; }}
    .icon {{ font-size: 48px; margin-bottom: 8px; }}
    .btn {{
      margin-top: 20px; border: none; background: #07c160; color: #fff; font-size: 15px;
      padding: 10px 28px; border-radius: 22px; cursor: pointer;
    }}
    .btn:active {{ opacity: .85; }}
  </style>
</head>
<body>
  {body}
</body>
</html>"""

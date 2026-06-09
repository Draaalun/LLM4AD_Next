"""
微信群活码公开扫码路由（公开端，免登录）。

用户扫描永久二维码后访问这里：
- ``GET /live-qr/{slug}``：返回移动端友好的落地页 HTML，内嵌当前有效群码并引导长按识别；
- ``GET /live-qr/{slug}/image``：返回按切换策略选出的当前有效真实群码图片，并累计扫码计数。

这两个端点不需要任何鉴权，且不出现在需要登录的体系内。
"""

import uuid

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep
from app.core.config import settings
from app.schemas import live_code as schemas
from app.services import live_code_service as service

router = APIRouter(prefix="/live-qr", tags=["live-qr"])

# 扫码去重 cookie 的有效期（秒）：同一客户端该窗口内重复扫码/刷新只计一次
SCAN_DEDUP_MAX_AGE = 30 * 24 * 3600  # 30 天


def _base_override(request: Request) -> str:
    """从请求推导对外基础 URL，作为未显式配置 FRONTEND_HOST 时的回退。"""
    return str(request.base_url).rstrip("/")


@router.get(
    "/contact",
    response_model=list[schemas.LiveCodeContactInfo],
    summary="联系我们活码信息（公开）",
)
def contact(db: SessionDep):
    """返回全部被标记为『联系我们』的活码公开信息；未配置时返回空列表。

    支持同时展示多张联系二维码，按创建时间正序排列。供前端「联系我们」面板拉取后
    渲染永久二维码与引导文案，无需鉴权。路由声明早于 ``/{slug}``，避免被动态路径吞掉。
    """
    live_codes = service.list_contact_live_codes(db)
    return [service.to_contact_info(lc) for lc in live_codes]


@router.get("/targets/{target_id}/image", summary="真实群码图片（公开）")
def target_image(target_id: uuid.UUID, db: SessionDep):
    """按 target_id 返回真实群码图片，免鉴权、内联、不计扫码数。

    群码本就是供终端用户扫码的公开内容；按不可枚举的 UUID 直取，便于管理后台与
    其它场景直接用 ``<img>`` 展示，无需携带令牌。路径段数与 ``/{slug}`` 不同，无冲突。
    """
    result = service.get_target_image_by_id(db, target_id)
    if result is None:
        return Response(status_code=404, headers={"Cache-Control": "no-store"})
    data, content_type = result
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "no-store"})


@router.get("/{slug}", response_class=HTMLResponse, summary="活码落地页")
def landing(slug: str, db: SessionDep, request: Request):
    """渲染活码落地页：展示当前有效群码与长按识别引导，永久不变。"""
    html_content, status_code = service.render_landing_page(db, slug, _base_override(request))
    return HTMLResponse(
        content=html_content,
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{slug}/image", summary="当前有效群码图片")
def scan_image(slug: str, db: SessionDep, request: Request):
    """返回当前有效的真实群码图片，并累计扫码计数（同一客户端去重）。

    去重：首次扫码后给浏览器下发 cookie ``lcq_{slug}``；带着该 cookie 的后续请求
    （重复扫码 / 刷新落地页）只返图、不再 +1。这样把"扫码次数"近似为"独立客户端数"，
    避免同一人反复刷新虚高。换设备 / 清 cookie 仍会重新计一次——这是无法从微信侧获知
    真实进群的固有近似，最终以管理员看到的实际群人数为准。

    活码不存在/停用/无有效群码时返回 404，由落地页负责降级展示。
    """
    cookie_name = f"lcq_{slug}"
    already_counted = request.cookies.get(cookie_name) is not None

    result = service.serve_scan(db, slug, count=not already_counted)
    if result is None:
        return Response(status_code=404, headers={"Cache-Control": "no-store"})

    data, content_type = result
    response = Response(content=data, media_type=content_type, headers={"Cache-Control": "no-store"})
    # 仅在本次实际计了数时下发去重 cookie；无有效群码时不下发，便于管理员补码后能再计一次
    if not already_counted:
        response.set_cookie(
            key=cookie_name,
            value="1",
            max_age=SCAN_DEDUP_MAX_AGE,
            path=f"{settings.API_V1_STR}/live-qr/{slug}/image",
            httponly=True,
            samesite="lax",
        )
    return response


@router.get("/{slug}/qrcode", summary="活码永久二维码 PNG（公开）")
def public_qrcode(slug: str, db: SessionDep, request: Request):
    """返回活码的永久二维码 PNG（编码对外落地页 URL），免鉴权可直接用于 ``<img>``。

    仅编码一个公开 URL，公开暴露无敏感信息。允许浏览器缓存以降低重复生成开销。
    """
    live_code = service.get_live_code_by_slug(db, slug)
    if not live_code:
        return Response(status_code=404, headers={"Cache-Control": "no-store"})
    public_url = service.build_public_url(slug, _base_override(request))
    png = service.generate_permanent_qr_png(public_url)
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )

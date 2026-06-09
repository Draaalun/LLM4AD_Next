"""
意见反馈路由。

提供反馈的创建、查询、更新、删除等端点。
普通用户可以提交和查看自己的反馈，管理员可以管理所有反馈。
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func
from sqlmodel import select

from app.api.deps import CurrentUser, OptionalUser, SessionDep
from app.models import (
    Feedback,
    FeedbackAdmin,
    FeedbackCreate,
    FeedbackPriority,
    FeedbackPublic,
    FeedbacksPublic,
    FeedbackStatistics,
    FeedbackStatus,
    FeedbackType,
    FeedbackUpdate,
    Message,
    User,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post(
    "/",
    response_model=FeedbackPublic,
    status_code=status.HTTP_201_CREATED,
    summary="提交意见反馈",
)
def create_feedback(
    feedback_in: FeedbackCreate,
    db: SessionDep,
    current_user: OptionalUser = None,
):
    """提交新的意见反馈。

    支持匿名反馈（不传 token）和登录用户反馈。
    匿名反馈建议填写联系方式以便后续沟通。

    Args:
        feedback_in: 反馈创建请求体。
        db: 数据库会话依赖。
        current_user: 当前登录用户（可选）。

    Returns:
        FeedbackPublic: 新创建反馈的响应数据。
    """
    feedback = Feedback.model_validate(
        feedback_in,
        update={"user_id": current_user.id if current_user else None},
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # 构造响应，填充用户信息
    response = FeedbackPublic.model_validate(feedback)
    if current_user:
        response.user_email = current_user.email
        response.user_full_name = current_user.full_name

    return response


@router.get(
    "/",
    response_model=FeedbacksPublic,
    summary="查询反馈列表",
)
def list_feedbacks(
    db: SessionDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(20, ge=1, le=100, description="单页最大返回数量"),
    type: FeedbackType | None = Query(None, description="按类型过滤"),
    status: FeedbackStatus | None = Query(None, description="按状态过滤"),
    priority: FeedbackPriority | None = Query(None, description="按优先级过滤"),
):
    """查询反馈列表。

    普通用户只能查看自己的反馈，管理员可以查看所有反馈。

    Args:
        db: 数据库会话依赖。
        current_user: 当前登录用户。
        skip: 跳过的记录数。
        limit: 单页最大返回数量。
        type: 按类型过滤。
        status: 按状态过滤。
        priority: 按优先级过滤。

    Returns:
        FeedbacksPublic: 分页结果。
    """
    query = select(Feedback, User).outerjoin(User, Feedback.user_id == User.id)

    # 非管理员只能查看自己的反馈
    if not current_user.is_superuser:
        query = query.where(Feedback.user_id == current_user.id)

    # 应用过滤条件
    if type:
        query = query.where(Feedback.type == type)
    if status:
        query = query.where(Feedback.status == status)
    if priority:
        query = query.where(Feedback.priority == priority)

    # 查询总数
    count_query = select(func.count()).select_from(Feedback)
    if not current_user.is_superuser:
        count_query = count_query.where(Feedback.user_id == current_user.id)
    if type:
        count_query = count_query.where(Feedback.type == type)
    if status:
        count_query = count_query.where(Feedback.status == status)
    if priority:
        count_query = count_query.where(Feedback.priority == priority)
    total = db.exec(count_query).one()

    # 分页查询
    query = query.order_by(Feedback.created_time.desc()).offset(skip).limit(limit)
    results = db.exec(query).all()

    # 构造响应，填充用户信息
    items = []
    for feedback, user in results:
        item = FeedbackPublic.model_validate(feedback)
        if user:
            item.user_email = user.email
            item.user_full_name = user.full_name
        items.append(item)

    return FeedbacksPublic(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/statistics",
    response_model=FeedbackStatistics,
    summary="获取反馈统计信息（管理员）",
)
def get_feedback_statistics(
    db: SessionDep,
    current_user: CurrentUser,
):
    """获取反馈统计信息。

    仅管理员可访问，返回各状态、类型、优先级的反馈数量统计。

    Args:
        db: 数据库会话依赖。
        current_user: 当前登录用户。

    Returns:
        FeedbackStatistics: 统计信息。

    Raises:
        HTTPException: 403 如果用户不是管理员。
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access statistics",
        )

    # 查询所有反馈
    feedbacks = db.exec(select(Feedback)).all()

    # 统计各状态数量
    status_counts = {
        "pending": 0,
        "in_progress": 0,
        "resolved": 0,
        "closed": 0,
        "rejected": 0,
    }
    for feedback in feedbacks:
        status_counts[feedback.status] += 1

    # 统计各类型数量
    type_counts = {}
    for feedback in feedbacks:
        type_counts[feedback.type] = type_counts.get(feedback.type, 0) + 1

    # 统计各优先级数量
    priority_counts = {}
    for feedback in feedbacks:
        priority_counts[feedback.priority] = priority_counts.get(feedback.priority, 0) + 1

    return FeedbackStatistics(
        total=len(feedbacks),
        pending=status_counts["pending"],
        in_progress=status_counts["in_progress"],
        resolved=status_counts["resolved"],
        closed=status_counts["closed"],
        rejected=status_counts["rejected"],
        by_type=type_counts,
        by_priority=priority_counts,
    )


@router.get(
    "/{feedback_id}",
    response_model=FeedbackAdmin,
    summary="获取反馈详情",
)
def get_feedback(
    feedback_id: uuid.UUID,
    db: SessionDep,
    current_user: CurrentUser,
):
    """获取单个反馈的详细信息。

    普通用户只能查看自己的反馈，管理员可以查看所有反馈。
    管理员返回包含 internal_notes 的完整信息。

    Args:
        feedback_id: 反馈 ID。
        db: 数据库会话依赖。
        current_user: 当前登录用户。

    Returns:
        FeedbackAdmin: 反馈详情。

    Raises:
        HTTPException: 404 如果反馈不存在，403 如果无权访问。
    """
    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    # 检查权限
    if not current_user.is_superuser and feedback.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # 构造响应，填充用户信息
    response = FeedbackAdmin.model_validate(feedback)
    if not current_user.is_superuser:
        response.internal_notes = None
    if feedback.user_id:
        user = db.get(User, feedback.user_id)
        if user:
            response.user_email = user.email
            response.user_full_name = user.full_name

    return response


@router.patch(
    "/{feedback_id}",
    response_model=FeedbackAdmin,
    summary="更新反馈（管理员）",
)
def update_feedback(
    feedback_id: uuid.UUID,
    feedback_update: FeedbackUpdate,
    db: SessionDep,
    current_user: CurrentUser,
):
    """更新反馈信息。

    仅管理员可以更新反馈状态、优先级、回复等信息。
    更新状态为已解决时自动记录解决时间。

    Args:
        feedback_id: 反馈 ID。
        feedback_update: 更新请求体。
        db: 数据库会话依赖。
        current_user: 当前登录用户。

    Returns:
        FeedbackAdmin: 更新后的反馈信息。

    Raises:
        HTTPException: 403 如果用户不是管理员，404 如果反馈不存在。
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update feedback",
        )

    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    # 更新字段
    update_data = feedback_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(feedback, key, value)

    # 如果有回复，记录管理员 ID
    if feedback_update.admin_reply is not None:
        feedback.admin_id = current_user.id

    # 如果状态变为已解决，记录解决时间
    if feedback_update.status == FeedbackStatus.RESOLVED and not feedback.resolved_time:
        from datetime import UTC, datetime
        feedback.resolved_time = datetime.now(UTC)

    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.delete(
    "/{feedback_id}",
    response_model=Message,
    summary="删除反馈（管理员）",
)
def delete_feedback(
    feedback_id: uuid.UUID,
    db: SessionDep,
    current_user: CurrentUser,
):
    """删除反馈。

    仅管理员可以删除反馈。建议使用状态管理而非物理删除。

    Args:
        feedback_id: 反馈 ID。
        db: 数据库会话依赖。
        current_user: 当前登录用户。

    Returns:
        Message: 删除成功消息。

    Raises:
        HTTPException: 403 如果用户不是管理员，404 如果反馈不存在。
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete feedback",
        )

    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )

    db.delete(feedback)
    db.commit()
    return Message(message="Feedback deleted successfully")

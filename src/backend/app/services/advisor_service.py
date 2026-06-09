"""进化块分析建议 Service。

负责 block advise 和 block recommend 的后台生成、Provider 配置解析、
S3 数据下载到临时目录以及结果持久化。
"""

import asyncio
import copy
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app import models
from app.core.storage import storage
from app.schemas.advisor import (
    AdvisorDetailResponse,
    AdvisorGenerateRequest,
    AdvisorGenerateResponse,
)
from app.schemas.report import ReportStatus
from app.services.report_service import _resolve_provider_config
from app.services.task_service import get_task_with_auth

ADVISOR_TYPE_ADVISE = "block_advise"
ADVISOR_TYPE_RECOMMEND = "block_recommend"


def generate_advise(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    request: AdvisorGenerateRequest,
    access_token: str | None = None,
) -> AdvisorGenerateResponse:
    """校验输入并启动后台 advise 生成任务。

    Args:
        db: 数据库会话。
        task_id: 目标任务 ID。
        current_user: 当前认证用户。
        request: 生成请求。
        access_token: 当前登录 token，用于替换内置供应商 URL 中的占位。

    Returns:
        状态为 generating 的响应。
    """
    task = get_task_with_auth(db, task_id, current_user)
    _validate_task_has_data(task)

    provider_config = _resolve_provider_config(
        db,
        current_user,
        task,
        request.provider_id,
        request.model_name,
        access_token,
    )

    _set_generating_status(db, task, ADVISOR_TYPE_ADVISE, request, provider_config)

    asyncio.get_event_loop().create_task(
        _run_advise_generation(
            task_id=task_id,
            provider_config=provider_config,
            goal=request.goal,
            input_data_path=task.input_data_path,
            language=request.language,
        )
    )

    return AdvisorGenerateResponse(
        task_id=task_id,
        advisor_type=ADVISOR_TYPE_ADVISE,
        status=ReportStatus.GENERATING,
        message="Block advise generation started",
    )


def generate_recommend(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    request: AdvisorGenerateRequest,
    access_token: str | None = None,
) -> AdvisorGenerateResponse:
    """校验输入并启动后台 recommend 生成任务。

    Args:
        db: 数据库会话。
        task_id: 目标任务 ID。
        current_user: 当前认证用户。
        request: 生成请求。
        access_token: 当前登录 token，用于替换内置供应商 URL 中的占位。

    Returns:
        状态为 generating 的响应。
    """
    task = get_task_with_auth(db, task_id, current_user)
    _validate_task_has_data(task)

    provider_config = _resolve_provider_config(
        db,
        current_user,
        task,
        request.provider_id,
        request.model_name,
        access_token,
    )

    _set_generating_status(db, task, ADVISOR_TYPE_RECOMMEND, request, provider_config)

    asyncio.get_event_loop().create_task(
        _run_recommend_generation(
            task_id=task_id,
            provider_config=provider_config,
            goal=request.goal,
            input_data_path=task.input_data_path,
            language=request.language,
        )
    )

    return AdvisorGenerateResponse(
        task_id=task_id,
        advisor_type=ADVISOR_TYPE_RECOMMEND,
        status=ReportStatus.GENERATING,
        message="Block recommend generation started",
    )


def get_advisor_result(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    advisor_type: str,
) -> AdvisorDetailResponse:
    """从任务的 reports 字典中读取指定类型的 advisor 结果。

    Args:
        db: 数据库会话。
        task_id: 目标任务 ID。
        current_user: 当前认证用户。
        advisor_type: 'block_advise' 或 'block_recommend'。

    Returns:
        包含结果数据的响应。
    """
    task = get_task_with_auth(db, task_id, current_user)
    entry = (task.reports or {}).get(advisor_type)

    if not entry:
        return AdvisorDetailResponse(task_id=task_id, advisor_type=advisor_type)

    return AdvisorDetailResponse(
        task_id=task_id,
        advisor_type=advisor_type,
        status=ReportStatus(entry["status"]) if entry.get("status") else None,
        data=entry.get("data"),
        error=entry.get("error"),
        updated_at=entry.get("updated_at"),
    )


# ---- Background generation coroutines ----


async def _run_advise_generation(
    task_id: uuid.UUID,
    provider_config: dict[str, Any],
    goal: str,
    input_data_path: str,
    language:str,
) -> None:
    """后台协程：下载 S3 数据到临时目录，调用 advise_block，持久化结果。"""
    temp_dir = None
    try:
        temp_dir = await asyncio.to_thread(_download_task_data, input_data_path)

        from llm4ad.advisor.pipeline import advise_blocks

        advice = await advise_blocks(
            goal,
            repo_path=temp_dir,
            api_key=provider_config.get("api_key"),
            model=provider_config.get("model"),
            base_url=provider_config.get("base_url"),
            provider_type=provider_config.get("type", "openai_compatible"),
            lang=language,
        )

        _persist_advisor_result(
            task_id,
            ADVISOR_TYPE_ADVISE,
            ReportStatus.COMPLETED,
            advice.to_dict(),
        )

    except Exception as exc:
        logger.exception(f"Advise generation failed: task_id={task_id}")
        _persist_advisor_result(
            task_id,
            ADVISOR_TYPE_ADVISE,
            ReportStatus.FAILED,
            None,
            error=str(exc),
        )
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


async def _run_recommend_generation(
    task_id: uuid.UUID,
    provider_config: dict[str, Any],
    goal: str,
    input_data_path: str,
    language: str
) -> None:
    """后台协程：下载 S3 数据到临时目录，调用 recommend_blocks，持久化结果。"""
    temp_dir = None
    try:
        temp_dir = await asyncio.to_thread(_download_task_data, input_data_path)

        from llm4ad.advisor.recommender import recommend_blocks
        from llm4ad.infra.repo_analyzer import clean_path

        result = clean_path(
            temp_dir,
            apply=True,
            include=None,
            exclude=None,
        )

        result = await recommend_blocks(
            goal,
            repo_path=temp_dir,
            api_key=provider_config.get("api_key"),
            model=provider_config.get("model"),
            base_url=provider_config.get("base_url"),
            provider_type=provider_config.get("type", "openai_compatible"),
            lang=language,
        )

        _persist_advisor_result(
            task_id,
            ADVISOR_TYPE_RECOMMEND,
            ReportStatus.COMPLETED,
            result.to_dict(),
        )

    except Exception as exc:
        logger.exception(f"Recommend generation failed: task_id={task_id}")
        _persist_advisor_result(
            task_id,
            ADVISOR_TYPE_RECOMMEND,
            ReportStatus.FAILED,
            None,
            error=str(exc),
        )
    finally:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


# ---- Helper functions ----


def _validate_task_has_data(task: models.Task) -> None:
    """校验任务包含数据文件。"""
    if not task.input_data_path:
        raise HTTPException(
            status_code=400,
            detail="Task has no input data. Please upload data files first.",
        )


def _set_generating_status(
    db: Session,
    task: models.Task,
    advisor_type: str,
    request: AdvisorGenerateRequest,
    provider_config: dict[str, Any],
) -> None:
    """在 task.reports 中设置 generating 状态。"""
    now = datetime.now(UTC).isoformat()
    entry = {
        "status": ReportStatus.GENERATING.value,
        "data": None,
        "created_at": now,
        "updated_at": now,
        "error": None,
        "params": {
            "goal": request.goal,
            "language": request.language,
            "provider_model": provider_config.get("model", ""),
        },
    }

    if task.reports is None:
        task.reports = {}
    task.reports = {**task.reports, advisor_type: entry}
    db.add(task)
    db.commit()


def _download_task_data(input_data_path: str) -> str:
    """将 S3 中的任务数据下载到临时目录，返回临时目录路径。"""
    temp_dir = tempfile.mkdtemp(prefix="llm4ad_advisor_")
    success = storage.download_files_local(input_data_path, temp_dir)
    if not success:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"No files found in S3 at path: {input_data_path}")
    return temp_dir


def _persist_advisor_result(
    task_id: uuid.UUID,
    advisor_type: str,
    status: ReportStatus,
    data: dict[str, Any] | None,
    error: str | None = None,
) -> None:
    """新开数据库会话，将 advisor 结果持久化到 task.reports。"""
    from app.core.db import engine

    with Session(engine) as db:
        task = db.get(models.Task, task_id)
        if not task:
            logger.warning(f"Task {task_id} not found when persisting advisor result")
            return

        reports = copy.deepcopy(dict(task.reports or {}))
        entry = reports.get(advisor_type, {})
        entry["status"] = status.value
        entry["data"] = data
        entry["updated_at"] = datetime.now(UTC).isoformat()
        entry["error"] = error
        reports[advisor_type] = entry
        task.reports = reports
        flag_modified(task, "reports")
        db.add(task)
        db.commit()

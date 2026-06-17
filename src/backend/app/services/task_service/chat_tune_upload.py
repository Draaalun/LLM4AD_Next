"""调参对话（Chat Tune）中的文件与目录上传。

校验调参消息归属与 payload ``cardId`` 后，把文件/目录上传到任务数据的第一个
子目录，并将生成的路径写回对应 payload 选项。
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select

from app import models
from app.core.storage import storage
from app.schemas import task as schemas

from ._helpers import (
    _backfill_empty_parent,
    _check_file_size,
    _check_storage_quota,
    _remove_placeholder_if_present,
    _resolve_first_subdir,
)
from .auth import get_task_with_auth


def _validate_chat_tune_message(
    db: Session,
    task: models.Task,
    message_id: uuid.UUID,
    card_id: str,
) -> Any:
    """校验调参消息归属与 payload cardId 一致性。

    Args:
        db: 数据库会话。
        task: 已通过权限校验的任务。
        message_id: 消息 ID。
        card_id: 前端卡片 ID，需与 payload.cardId 匹配。

    Returns:
        通过校验的 ChatTuneMessage 实例。

    Raises:
        HTTPException: 消息不存在、不属于当前任务、无 payload 或 cardId 不匹配。
    """
    from app.models.chat_tune import ChatTuneMessage, ChatTuneSession

    message = db.get(ChatTuneMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="消息不存在")

    # 校验消息归属当前任务的调参会话
    session = db.exec(
        select(ChatTuneSession).where(ChatTuneSession.task_id == task.id)
    ).first()
    if session is None or message.session_id != session.id:
        raise HTTPException(status_code=400, detail="该消息不属于当前任务的调参会话")

    # 校验 payload 及 cardId
    if not message.payload:
        raise HTTPException(status_code=400, detail="该消息没有可交互的 payload")
    if message.payload.get("cardId") != card_id:
        raise HTTPException(status_code=400, detail="cardId 不匹配")

    return message


def chat_tune_upload_file(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    message_id: uuid.UUID,
    card_id: str,
    option_index: int,
    files: list[UploadFile],
) -> schemas.ChatTuneUploadFileResponse:
    """调参对话中上传文件到任务数据的第一个子目录。

    校验消息归属与 payload cardId 后执行上传。若对应选项中已有
    ``file_path``，则先删除旧文件。上传完成后将新路径写入
    ``payload.options[option_index]`` 并持久化。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        message_id: 调参消息 ID。
        card_id: payload 卡片 ID。
        option_index: 选项在 payload.options 中的索引。
        files: 上传的文件列表。

    Returns:
        包含更新后 payload 的响应。
    """
    from copy import deepcopy

    from sqlalchemy.orm.attributes import flag_modified

    task = get_task_with_auth(db, task_id, current_user)
    if not task.input_data_path:
        raise HTTPException(status_code=400, detail="任务尚未初始化数据目录，无法上传")

    message = _validate_chat_tune_message(db, task, message_id, card_id)

    if not files:
        raise HTTPException(status_code=400, detail="至少上传一个文件")

    # 校验单文件大小和总存储配额
    total_upload_size = 0
    for f in files:
        f.file.seek(0, 2)
        size = f.file.tell()
        f.file.seek(0)
        _check_file_size(size)
        total_upload_size += size
    _check_storage_quota(task.input_data_path, total_upload_size)

    subdir = _resolve_first_subdir(task.input_data_path)
    prefix = task.input_data_path

    # 若对应选项中已有 file_path，先删除旧文件
    payload = deepcopy(message.payload)
    options = payload.get("options")
    if not options or option_index < 0 or option_index >= len(options):
        raise HTTPException(status_code=400, detail="option_index 超出范围")
    option = options[option_index]
    old_file_path = option.get("file_path")
    if old_file_path:
        old_key = f"{prefix}/{old_file_path}".replace("//", "/")
        existing = storage.list_objects(prefix=old_key)
        if old_key in existing:
            storage.delete(old_key)
            _backfill_empty_parent(prefix, old_file_path)

    # 上传文件
    storage.ensure_bucket()
    relative_paths: list[str] = []
    for f in files:
        relative = f"{subdir}/{f.filename}"
        key = f"{prefix}/{relative}".replace("//", "/")
        storage.upload(key, f.file, content_type=f.content_type)
        relative_paths.append(relative)

    _remove_placeholder_if_present(prefix, subdir)

    # 更新对应选项的 file_path 并持久化
    option["file_path"] = relative_paths[0] if len(relative_paths) == 1 else relative_paths
    payload["options"][option_index] = option
    message.payload = payload
    message.updated_time = datetime.now(UTC)
    flag_modified(message, "payload")
    db.add(message)
    db.commit()
    db.refresh(message)

    return schemas.ChatTuneUploadFileResponse(payload=message.payload)


def chat_tune_upload_data(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    message_id: uuid.UUID,
    card_id: str,
    option_index: int,
    files: list[UploadFile],
) -> schemas.ChatTuneUploadDataResponse:
    """调参对话中上传目录到任务数据的第一个子目录。

    上传逻辑与前端 ``upload-data`` 一致（多文件、filename 保留目录结构）。
    校验消息归属与 payload cardId 后执行上传。若对应选项中已有
    ``dir_path``，则先递归删除旧目录。上传完成后将新路径写入
    ``payload.options[option_index]`` 并持久化。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        message_id: 调参消息 ID。
        card_id: payload 卡片 ID。
        option_index: 选项在 payload.options 中的索引。
        files: 上传的文件列表（filename 可含 ``/`` 以表达子目录结构）。

    Returns:
        包含更新后 payload 的响应。
    """
    from copy import deepcopy

    from sqlalchemy.orm.attributes import flag_modified

    task = get_task_with_auth(db, task_id, current_user)
    if not task.input_data_path:
        raise HTTPException(status_code=400, detail="任务尚未初始化数据目录，无法上传")

    message = _validate_chat_tune_message(db, task, message_id, card_id)

    if not files:
        raise HTTPException(status_code=400, detail="至少上传一个文件")
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="单次上传文件数量不能超过 100 个")

    # 校验单文件大小和总存储配额
    total_upload_size = 0
    for f in files:
        f.file.seek(0, 2)
        size = f.file.tell()
        f.file.seek(0)
        _check_file_size(size)
        total_upload_size += size
    _check_storage_quota(task.input_data_path, total_upload_size)

    subdir = _resolve_first_subdir(task.input_data_path)
    prefix = task.input_data_path

    # 若对应选项中已有 dir_path，先递归删除旧目录
    payload = deepcopy(message.payload)
    options = payload.get("options")
    if not options or option_index < 0 or option_index >= len(options):
        raise HTTPException(status_code=400, detail="option_index 超出范围")
    option = options[option_index]
    old_dir_path = option.get("dir_path")
    if old_dir_path:
        old_dir_prefix = f"{prefix}/{old_dir_path}/"
        old_keys = storage.list_objects(prefix=old_dir_prefix)
        for key in old_keys:
            storage.delete(key)
        if old_keys:
            _backfill_empty_parent(prefix, old_dir_path)

    # 上传目录
    storage.ensure_bucket()
    upload_prefix = f"{prefix}/{subdir}"
    storage.upload_files(
        prefix=upload_prefix,
        files=[(f.filename, f.file, f.content_type) for f in files],
    )

    _remove_placeholder_if_present(prefix, subdir)

    # 提取上传后的顶级目录名作为 dir_path
    top_dirs: set[str] = set()
    for f in files:
        if f.filename and "/" in f.filename:
            top_dirs.add(f.filename.split("/", 1)[0])
    if top_dirs:
        dir_path = f"{subdir}/{sorted(top_dirs)[0]}"
    else:
        dir_path = subdir

    # 更新对应选项的 dir_path 并持久化
    option["dir_path"] = dir_path
    payload["options"][option_index] = option
    message.payload = payload
    message.updated_time = datetime.now(UTC)
    flag_modified(message, "payload")
    db.add(message)
    db.commit()
    db.refresh(message)

    return schemas.ChatTuneUploadDataResponse(payload=message.payload)

"""存储/文件管理相关的公共助手与常量。

集中放置占位文件处理、路径校验、配额校验、目录树构建等被
``files`` / ``templates`` / ``crud`` / ``chat_tune_upload`` 等多个子模块复用的
底层工具。仅依赖 ``auth.get_task_with_auth``，不反向依赖业务子模块。
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import Session

from app import models
from app.core.config import settings
from app.core.storage import storage

from .auth import get_task_with_auth

# 占位文件名：用于在对象存储中标记空文件夹的存在
PLACEHOLDER_NAME = ".keep"

_MAX_FILE_BYTES = settings.TASK_MAX_FILE_SIZE_MB * 1024 * 1024
_MAX_STORAGE_BYTES = settings.TASK_MAX_STORAGE_MB * 1024 * 1024

# 新建任务时自动创建的顶级文件夹名称
DEFAULT_TOP_FOLDER_NAME = "code"

_FOLDER_NAME_BASE = "new_folder"

_DEFAULT_FILE_CONTENT = '''\
def main():
    print("Hello, World!")


# 可通过一级目录下的 requirements.txt 文件指定依赖。
if __name__ == "__main__":
    main()
'''


def _validate_file_path(file_path: str) -> None:
    """校验文件路径安全性，防止路径穿越。

    使用 PurePosixPath 做规范化后逐段检查，防御 URL 编码绕过等攻击。
    """
    from pathlib import PurePosixPath

    if not file_path or not file_path.strip():
        raise HTTPException(status_code=400, detail="文件路径不能为空")
    normalized = PurePosixPath(file_path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise HTTPException(status_code=400, detail="非法文件路径")


def _is_placeholder_key(key: str) -> bool:
    """判断 S3 key 是否为空文件夹占位文件。"""
    return key.endswith("/" + PLACEHOLDER_NAME) or key == PLACEHOLDER_NAME


def _is_placeholder_relative(relative_path: str) -> bool:
    """判断相对路径是否指向占位文件。"""
    name = relative_path.rsplit("/", 1)[-1] if "/" in relative_path else relative_path
    return name == PLACEHOLDER_NAME


def _reject_placeholder_path(file_path: str) -> None:
    """拒绝直接通过文件接口操作占位文件，引导用户使用文件夹接口。"""
    if _is_placeholder_relative(file_path):
        raise HTTPException(
            status_code=400,
            detail=f"{PLACEHOLDER_NAME} 为空文件夹占位文件，请使用文件夹接口管理目录",
        )


def _check_file_size(size: int) -> None:
    """校验单个文件大小是否超出限制。"""
    if size > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小 {size / 1024 / 1024:.1f}MB 超出单文件限制 {settings.TASK_MAX_FILE_SIZE_MB}MB",
        )


def _check_storage_quota(prefix: str, additional_bytes: int) -> None:
    """校验追加数据后是否超出任务总存储限制。"""
    current = storage.get_prefix_total_size(prefix)
    if current + additional_bytes > _MAX_STORAGE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"任务存储空间不足：当前已用 {current / 1024 / 1024:.1f}MB，"
                f"本次需要 {additional_bytes / 1024 / 1024:.1f}MB，"
                f"总限制 {settings.TASK_MAX_STORAGE_MB}MB"
            ),
        )


def _backfill_empty_parent(prefix: str, child_path: str) -> None:
    """若 child_path 的父目录在操作后变为空，则补一个占位文件以保留目录结构。

    Args:
        prefix: 任务输入数据根前缀（不带尾部斜杠）。
        child_path: 被删除/移动的文件或文件夹的相对路径。
    """
    parent_dir = child_path.rsplit("/", 1)[0] if "/" in child_path else ""
    if not parent_dir:
        return
    parent_prefix = f"{prefix}/{parent_dir}/"
    remaining = storage.list_objects(prefix=parent_prefix)
    if not remaining:
        placeholder_key = f"{parent_prefix}{PLACEHOLDER_NAME}"
        storage.upload(placeholder_key, b"", content_type="text/plain; charset=utf-8")


def _normalize_dir_path(path: str | None) -> str:
    """规范化目录相对路径：去掉首尾斜杠，空值返回空字符串。"""
    if not path:
        return ""
    return path.strip("/").strip()


def _remove_placeholder_if_present(prefix: str, target_dir: str) -> None:
    """若指定目录下存在占位文件，则将其删除。

    Args:
        prefix: 任务输入数据根前缀（不带尾部斜杠）。
        target_dir: 目录相对路径，空字符串表示根目录。
    """
    placeholder_key = (
        f"{prefix}/{target_dir}/{PLACEHOLDER_NAME}" if target_dir else f"{prefix}/{PLACEHOLDER_NAME}"
    )
    placeholder_key = placeholder_key.replace("//", "/")
    existing = storage.list_objects(prefix=placeholder_key)
    if placeholder_key in existing:
        storage.delete(placeholder_key)


def _get_task_input_data_path(db: Session, task_id: uuid.UUID, current_user: models.User) -> tuple[models.Task, str]:
    """获取任务并验证 input_data_path 存在。"""
    task = get_task_with_auth(db, task_id, current_user)
    if not task.input_data_path:
        raise HTTPException(status_code=404, detail="该任务没有上传输入数据")
    return task, task.input_data_path


def _build_file_tree(keys: list[str], prefix: str) -> list[dict]:
    """将扁平的 S3 key 列表构建为嵌套的树形结构。

    占位文件（``.keep``）仅用于标记空文件夹的存在，不会作为节点暴露给前端，
    但其所在的目录链路会被保留为 ``directory`` 节点（可能为空目录）。

    内部表示：``tree`` 为嵌套字典，``None`` 值表示文件，``dict`` 值表示目录。
    """
    tree: dict = {}
    prefix = prefix.rstrip("/") + "/"

    def ensure_dir(node: dict, name: str) -> dict:
        existing = node.get(name)
        if isinstance(existing, dict):
            return existing
        new_dir: dict = {}
        node[name] = new_dir
        return new_dir

    for key in keys:
        relative = key[len(prefix) :]
        if not relative:
            continue
        parts = relative.split("/")
        is_placeholder = parts[-1] == PLACEHOLDER_NAME
        if is_placeholder:
            # 占位文件只用于标记目录存在，丢弃文件名段，仅保留目录链路
            parts = parts[:-1]
            if not parts:
                continue
            node = tree
            for part in parts:
                node = ensure_dir(node, part)
            continue
        node = tree
        for part in parts[:-1]:
            node = ensure_dir(node, part)
        # 末段是文件名：仅当当前不是目录时才标记为文件
        leaf = parts[-1]
        if not isinstance(node.get(leaf), dict):
            node[leaf] = None

    def to_nodes(subtree: dict, parent_path: str) -> list[dict]:
        nodes = []
        for name, children in sorted(subtree.items()):
            path = f"{parent_path}/{name}" if parent_path else name
            if isinstance(children, dict):
                nodes.append(
                    {
                        "name": name,
                        "path": path,
                        "type": "directory",
                        "children": to_nodes(children, path),
                    }
                )
            else:
                nodes.append(
                    {
                        "name": name,
                        "path": path,
                        "type": "file",
                        "children": None,
                    }
                )
        return nodes

    return to_nodes(tree, "")


def _resolve_target_directory(path: str | None) -> str:
    """将用户选择的路径解析为目标目录。

    Args:
        path: 用户提供的路径，可以是文件路径、目录路径、空字符串或 None。

    Returns:
        目标目录的相对路径（根目录为空字符串）。
    """
    if not path or not path.strip():
        return ""
    raw = path
    stripped = raw.strip("/")
    if not stripped:
        return ""
    if raw.endswith("/"):
        return stripped
    parts = stripped.split("/")
    last = parts[-1]
    if "." in last:
        return "/".join(parts[:-1])
    return stripped


def _resolve_first_subdir(prefix: str) -> str:
    """返回 prefix 下第一个子目录名称，不存在时创建 ``code/`` 目录。

    Args:
        prefix: 任务的 ``input_data_path``（S3 key 前缀，不含尾部斜杠）。

    Returns:
        第一个子目录名称（按字母排序），例如 ``"code"``。
    """
    keys = storage.list_objects(prefix=f"{prefix}/")
    prefix_slash = prefix.rstrip("/") + "/"
    subdirs: set[str] = set()
    for key in keys:
        relative = key[len(prefix_slash):]
        if not relative or "/" not in relative:
            continue
        first_segment = relative.split("/", 1)[0]
        if first_segment and first_segment != PLACEHOLDER_NAME:
            subdirs.add(first_segment)
    if subdirs:
        return sorted(subdirs)[0]
    placeholder_key = f"{prefix}/{DEFAULT_TOP_FOLDER_NAME}/{PLACEHOLDER_NAME}"
    storage.upload(placeholder_key, b"", content_type="text/plain; charset=utf-8")
    return DEFAULT_TOP_FOLDER_NAME


def _validate_folder_name(name: str) -> None:
    """校验文件夹名称：非空、不含路径分隔符、不能是占位文件名。"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="文件夹名不能为空")
    if "/" in name or "\\" in name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="文件夹名不能包含路径分隔符或为相对路径")
    if name == PLACEHOLDER_NAME:
        raise HTTPException(status_code=400, detail=f"{PLACEHOLDER_NAME} 为保留名称")


def _ensure_input_data_prefix(db: Session, task: models.Task) -> str:
    """若任务尚无 ``input_data_path`` 则按时间戳生成并落库，返回当前 prefix。"""
    if task.input_data_path:
        return task.input_data_path
    ts = int(datetime.now(UTC).timestamp())
    prefix = f"tasks/{task.id}/{ts}"
    storage.ensure_bucket()
    task.input_data_path = prefix
    task.updated_time = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    return prefix


def _create_top_level_folder(db: Session, task: models.Task, name: str) -> str:
    """在任务输入数据根目录下创建一个顶级文件夹（占位文件方式）。

    用于新建任务时自动初始化一个顶级目录。若同名目录已存在则不重复写入。

    Args:
        db: 数据库会话。
        task: Task 模型实例（已持久化，拥有 id）。
        name: 顶级文件夹名称。

    Returns:
        已创建文件夹的相对路径。
    """
    prefix = _ensure_input_data_prefix(db, task)
    placeholder_key = f"{prefix}/{name}/{PLACEHOLDER_NAME}"
    existing = storage.list_objects(prefix=f"{prefix}/{name}/")
    if placeholder_key not in existing:
        storage.upload(placeholder_key, b"", content_type="text/plain; charset=utf-8")
    return name

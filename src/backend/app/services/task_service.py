"""
任务服务层。

封装任务相关的业务逻辑，包括创建、运行、状态查询、数据上传等。
将路由处理器中的复杂业务逻辑提取到此处，实现关注点分离。
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from celery.result import AsyncResult
from fastapi import HTTPException, Request, Response, UploadFile, status
from llm4ad.config import AppConfig
from llm4ad.config.app import EmbeddingConfig
from loguru import logger
from sqlalchemy import or_
from sqlmodel import Session, func, select

from app import models
from app.core.celery import celery_app
from app.core.config import settings
from app.core.constants import CELERY_STATUS_MAP
from app.core.redis import touch_code_user_active
from app.core.security import decode_access_token
from app.core.storage import storage
from app.models import Message, TaskStatus, User
from app.schemas import task as schemas
from app.services.project_service import get_project_with_auth
from app.tasks.evolution import run_evolution

if TYPE_CHECKING:
    from app.schemas.result_render import (
        ResultRenderGenerateRequest,
        ResultRenderGenerateResponse,
    )


def get_task_with_auth(db: Session, task_id: uuid.UUID, current_user: models.User) -> models.Task:
    """获取任务并通过所属项目校验权限。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户

    Returns:
        通过权限校验的任务对象

    Raises:
        HTTPException: 任务不存在（404）或无权访问（403）
    """
    task = db.get(models.Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    get_project_with_auth(db, task.project_id, current_user)
    return task


def get_task_storage_usage(task: models.Task) -> schemas.StorageUsage:
    """计算任务输入数据的存储用量。"""
    used = storage.get_prefix_total_size(task.input_data_path) if task.input_data_path else 0
    return schemas.StorageUsage(
        used_bytes=used,
        limit_bytes=_MAX_STORAGE_BYTES,
        used_mb=round(used / 1024 / 1024, 2),
        limit_mb=settings.TASK_MAX_STORAGE_MB,
    )


def get_active_status(db: Session, task: models.Task) -> TaskStatus:
    """返回任务当前活跃版本的状态。

    ``active_child_id`` 为空或指向自身时返回 ``task.status``；
    否则按 id 取出目标任务的状态。若目标任务异常缺失，回退到自身状态。
    """
    if task.active_child_id is None or task.active_child_id == task.id:
        return task.status
    active = db.get(models.Task, task.active_child_id)
    return active.status if active is not None else task.status


def list_tasks(
    db: Session,
    project_id: uuid.UUID,
    current_user: models.User,
    skip: int,
    limit: int,
) -> tuple[list[models.Task], int, dict[uuid.UUID, int], dict[uuid.UUID, TaskStatus]]:
    """分页查询项目下的任务列表。

    返回根任务列表本身的字段不会被改写；活跃版本（``active_child_id``
    指向的任务，为空时即任务自身）的状态通过 ``active_status_map`` 单独返回，
    供路由层填入响应的 ``active_status`` 字段。

    Args:
        db: 数据库会话。
        project_id: 项目 ID。
        current_user: 当前登录用户。
        skip: 跳过条数。
        limit: 每页条数。

    Returns:
        四元组 ``(tasks, total, children_count_map, active_status_map)``。
        ``active_status_map`` 的键为根任务 ID，值为对应活跃任务的状态。
    """
    get_project_with_auth(db, project_id, current_user)
    query = select(models.Task).where(
        models.Task.project_id == project_id,
        models.Task.parent_id.is_(None),  # type: ignore[union-attr]
    )
    total = db.exec(select(func.count()).select_from(query.subquery())).one()
    query = query.order_by(models.Task.created_time.desc())
    page_query = query.offset(skip).limit(limit) if limit > 0 else query
    tasks = list(db.exec(page_query).all())

    if not tasks:
        return tasks, total, {}, {}

    root_ids = [t.id for t in tasks]

    count_rows = db.exec(
        select(
            models.Task.group_id,
            func.count().label("cnt"),
        )
        .where(models.Task.group_id.in_(root_ids))
        .group_by(models.Task.group_id)
    ).all()
    count_map: dict[uuid.UUID, int] = {row.group_id: row.cnt for row in count_rows}

    # active_child_id 可能为空（视作指向自身），也可能指向某个子任务
    active_ids = {
        t.active_child_id for t in tasks
        if t.active_child_id is not None and t.active_child_id != t.id
    }
    id_to_status: dict[uuid.UUID, TaskStatus] = {}
    if active_ids:
        active_rows = db.exec(
            select(models.Task.id, models.Task.status).where(models.Task.id.in_(active_ids))
        ).all()
        id_to_status = {row.id: row.status for row in active_rows}

    active_status_map: dict[uuid.UUID, TaskStatus] = {}
    for t in tasks:
        if t.active_child_id is None or t.active_child_id == t.id:
            active_status_map[t.id] = t.status
        elif t.active_child_id in id_to_status:
            active_status_map[t.id] = id_to_status[t.active_child_id]
        else:
            # 指向的任务已不存在，回退到自身
            active_status_map[t.id] = t.status

    return tasks, total, count_map, active_status_map


EXAMPLES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "examples" / "applications"
    if settings.ENVIRONMENT == "local"
    else Path(__file__).resolve().parent.parent.parent / "examples" / "applications"
)


def list_example_templates() -> list[dict]:
    """列出可用的示例模板。

    扫描 examples 目录下的一级子目录，收集文件名以 config.yaml 结尾的文件作为配置模板。
    忽略没有配置文件的文件夹。每个配置文件分别读取自身的 description_en/description_zh
    字段，作为前端提示文字。

    Returns:
        按字母排序的模板列表，每项包含 name（文件夹名）和 configs（配置文件列表，
        每项含 name、description_en、description_zh）。
    """
    import yaml

    templates: list[dict] = []
    if not EXAMPLES_DIR.is_dir():
        return templates
    for entry in sorted(EXAMPLES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        config_files = sorted(f for f in entry.iterdir() if f.is_file() and f.name.endswith("config.yaml"))
        if not config_files:
            continue
        configs: list[dict] = []
        for config_path in config_files:
            description_en: str | None = None
            description_zh: str | None = None
            try:
                with open(config_path, encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                if isinstance(config_data, dict):
                    desc_en = config_data.get("description_en")
                    desc_zh = config_data.get("description_zh")
                    if isinstance(desc_en, str):
                        description_en = desc_en
                    if isinstance(desc_zh, str):
                        description_zh = desc_zh
            except (OSError, yaml.YAMLError) as exc:
                logger.warning(f"读取模板配置 '{entry.name}/{config_path.name}' 失败: {exc}")
            configs.append(
                {
                    "name": config_path.name,
                    "description_en": description_en,
                    "description_zh": description_zh,
                }
            )
        templates.append({"name": entry.name, "configs": configs})
    return templates


def _apply_template(db: Session, task: models.Task, template_name: str, config_name: str = "config.yaml") -> None:
    """上传模板文件到 S3 并根据配置文件更新任务的 input_args。

    Args:
        db: 数据库会话
        task: Task 模型实例（已持久化，拥有 id）
        template_name: 示例模板目录名称
        config_name: 配置文件名，默认为 config.yaml

    Raises:
        HTTPException: 模板不存在或缺少指定配置文件
    """
    import yaml

    template_dir = EXAMPLES_DIR / template_name
    if not template_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"模板 '{template_name}' 不存在")
    config_path = template_dir / config_name
    if not config_path.is_file():
        raise HTTPException(status_code=400, detail=f"模板 '{template_name}' 缺少 {config_name}")

    ts = int(datetime.now(UTC).timestamp())
    prefix = f"tasks/{task.id}/{ts}"
    storage.ensure_bucket()

    template_total_size = sum(f.stat().st_size for f in template_dir.rglob("*") if f.is_file())
    _check_storage_quota(prefix, template_total_size)

    for file_path in template_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.name.endswith("config.yaml"):
            continue
        relative = file_path.relative_to(template_dir).as_posix()
        key = f"{prefix}/{template_name}/{relative}"
        content_type = "application/octet-stream"
        if file_path.suffix in (".yaml", ".yml"):
            content_type = "text/yaml"
        elif file_path.suffix == ".json":
            content_type = "application/json"
        elif file_path.suffix == ".py":
            content_type = "text/x-python"
        elif file_path.suffix in (".txt", ".md", ".csv", ".log"):
            content_type = "text/plain"
        storage.upload(key, file_path.read_bytes(), content_type=content_type)

    task.input_data_path = prefix

    with open(config_path, encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    if isinstance(config_data, dict):
        # 前端提示文字字段不参与任务运行，保存到 input_args 前移除
        config_data.pop("description_en", None)
        config_data.pop("description_zh", None)
        if "planner" not in config_data:
            config_data["planner"] = {}
        if "coder" not in config_data:
            config_data["coder"] = {}
        # 除了mock，其它的都使用默认模型
        if config_data["planner"].get("provider") != "mock":
            config_data["planner"]["provider"] = "default"
            config_data["planner"]["provider_model"] = "" # 用于前端表单绑定
        if config_data["coder"].get("provider") != "mock":
            config_data["coder"]["provider"] = "default"
            config_data["coder"]["provider_model"] = ""
        config_data["providers"] = []
        task.input_args = config_data

    task.updated_time = datetime.now(UTC)
    db.add(task)


def create_task(db: Session, task_in: schemas.TaskCreate, current_user: models.User) -> models.Task:
    """创建任务，自动填充默认参数。

    当提供 template_name 时，会上传模板文件到存储，
    设置 input_data_path，并从 config.yaml 填充 input_args。

    Args:
        db: 数据库会话
        task_in: 任务创建请求数据
        current_user: 当前登录用户

    Returns:
        创建成功的任务对象
    """
    get_project_with_auth(db, task_in.project_id, current_user)

    input_args = task_in.input_args if task_in.input_args is not None else schemas.generate_default_input_args()

    # 处理供应商列表和模型选择，运行任务时需处理后传入llm4ad
    if "planner" not in input_args:
        input_args["planner"] = {}
    if "coder" not in input_args:
        input_args["coder"] = {}
    input_args["planner"]["provider"] = "default"
    input_args["coder"]["provider"] = "default"
    input_args["providers"] = []

    db_task = models.Task(
        name=task_in.name,
        description=task_in.description,
        project_id=task_in.project_id,
        input_args=input_args,
        status=TaskStatus.UNINITIALIZED,
        ai_built=task_in.ai_built,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    if task_in.template_name:
        config_name = task_in.config_name or "config.yaml"
        _apply_template(db, db_task, task_in.template_name, config_name)
        db.commit()
        db.refresh(db_task)
    else:
        # 非模板任务自动创建一个顶级文件夹；模板任务已有以模板名命名的顶级目录
        _create_top_level_folder(db, db_task, DEFAULT_TOP_FOLDER_NAME)
        db.commit()
        db.refresh(db_task)

    from app.services.chat_tune_service import seed_initial_messages

    seed_initial_messages(
        db,
        db_task,
        current_user,
        language=task_in.language,
        template_name=task_in.template_name,
        config_name=task_in.config_name or "config.yaml",
    )

    return db_task


def copy_task(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    is_child: bool = False,
) -> models.Task:
    """复制任务：名称加后缀，数据存在则在 S3 中复制一份，状态重置为 UNINITIALIZED。

    Args:
        db: 数据库会话
        task_id: 源任务 ID
        current_user: 当前登录用户
        is_child: 是否作为子任务复制；为 True 时保留父子关系和分组信息

    Returns:
        复制后的新任务对象
    """
    src_task = get_task_with_auth(db, task_id, current_user)

    # 如果原始任务有数据，复制 S3 文件
    new_data_path = None
    new_task_id = uuid.uuid4()
    if src_task.input_data_path:
        ts = int(datetime.now(UTC).timestamp())
        new_data_path = f"tasks/{new_task_id}/{ts}"
        storage.copy_objects(src_task.input_data_path, new_data_path)

    group_id = None
    parent_id = None
    if is_child:
        parent_id = src_task.id
        group_id = src_task.group_id if src_task.group_id else src_task.id

    new_task = models.Task(
        id=new_task_id,
        name=f"{src_task.name}-副本",
        description=src_task.description,
        project_id=src_task.project_id,
        input_args=src_task.input_args,
        input_data_path=new_data_path,
        reports=src_task.reports,
        status=TaskStatus.UNINITIALIZED,
        version_time=datetime.now(UTC),
        celery_task_id=None,
        group_id=group_id,
        parent_id=parent_id,
        ai_built=src_task.ai_built,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # 子任务复制时，同步复制源任务的日志记录关联到新任务
    if is_child:
        from app.models import TaskLog

        src_logs = db.exec(select(TaskLog).where(TaskLog.task_id == src_task.id)).all()
        for src_log in src_logs:
            db.add(
                TaskLog(
                    task_id=new_task.id,
                    type=src_log.type,
                    level=src_log.level,
                    timestamp=src_log.timestamp,
                    message=src_log.message,
                    data=src_log.data,
                )
            )

        # 自动将根任务的活跃子版本指向新创建的子任务
        root_id = group_id  # group_id 即根任务 ID
        root_task = db.get(models.Task, root_id)
        if root_task is not None:
            root_task.active_child_id = new_task.id
            root_task.updated_time = datetime.now(UTC)
            db.add(root_task)

        db.commit()
        db.refresh(new_task)

    return new_task


def update_task(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    task_update: schemas.TaskUpdate,
) -> models.Task:
    """修改任务参数，input_args 变更时同步更新 version_time。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户
        task_update: 任务更新请求数据

    Returns:
        更新后的任务对象
    """
    task = get_task_with_auth(db, task_id, current_user)

    update_data = task_update.model_dump(exclude_unset=True)
    task.sqlmodel_update(update_data)
    task.updated_time = datetime.now(UTC)
    # input_args 变更时更新版本时间
    if "input_args" in update_data:
        task.version_time = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task_tag(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    tag_update: schemas.TaskTagUpdate,
) -> models.Task:
    """更新任务的标签（tag）。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前认证用户。
        tag_update: 标签更新请求数据。

    Returns:
        更新后的任务对象。
    """
    task = get_task_with_auth(db, task_id, current_user)
    task.tag = tag_update.tag
    task.updated_time = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def set_active_child(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    child_id: uuid.UUID | None,
) -> models.Task:
    """设置根任务当前选中的子任务版本。

    Args:
        db: 数据库会话。
        task_id: 根任务 ID。
        current_user: 当前认证用户。
        child_id: 子任务 ID；为 None 时清空选中，读取时回退为指向自身。

    Returns:
        更新后的根任务对象。

    Raises:
        HTTPException 400: 目标任务不是根任务。
        HTTPException 404: 子任务不存在或不属于该根任务的分组。
    """
    task = get_task_with_auth(db, task_id, current_user)
    if task.parent_id is not None:
        raise HTTPException(status_code=400, detail="仅根任务支持设置活跃子版本")

    if child_id is not None:
        child = db.get(models.Task, child_id)
        if child is None or child.group_id != task.id:
            raise HTTPException(
                status_code=404, detail="子任务不存在或不属于该任务的版本组"
            )

    task.active_child_id = child_id
    task.updated_time = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task_tree(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
) -> schemas.TaskTreeResponse:
    """获取以指定任务为根的任务树。

    返回根任务以及所有 ``group_id`` 等于该根任务 ID 的子任务。
    每个条目仅包含轻量字段（不含 logs/results）。

    Args:
        db: 数据库会话。
        task_id: 根任务 ID。
        current_user: 当前认证用户。

    Returns:
        包含根节点与子节点列表的 ``TaskTreeResponse``。
    """
    root_task = get_task_with_auth(db, task_id, current_user)

    if root_task.parent_id is not None:
        raise HTTPException(status_code=400, detail="指定的任务不是根任务")

    children = db.exec(
        select(models.Task).where(models.Task.group_id == root_task.id).order_by(models.Task.created_time.asc())
    ).all()

    # 首次访问且有子任务时，自动选中最新子任务
    if root_task.active_child_id is None and children:
        latest = max(children, key=lambda c: c.created_time)
        root_task.active_child_id = latest.id
        root_task.updated_time = datetime.now(UTC)
        db.add(root_task)
        db.commit()
        db.refresh(root_task)

    return schemas.TaskTreeResponse(
        root=schemas.TaskTreeItem.model_validate(root_task),
        children=[schemas.TaskTreeItem.model_validate(c) for c in children],
    )


def _resolve_providers(
    db: Session,
    input_args: dict,
    current_user: models.User,
    access_token: str | None = None,
) -> dict:
    """解析供应商列表并处理 planner/coder 中的供应商引用，用于构建 run_args。

    1. 从当前用户的 LLMProvider 记录构建 ``input_args["providers"]``。
       每个供应商可包含多个模型（以 ``;`` 分隔），每个模型拆分为独立的
       ProviderConfig，name 格式为 ``{provider.id}{model}``。
    2. 解析 ``planner.provider`` / ``coder.provider``：
       - ``"default"`` 或空：从 UserDefaultModel 读取默认配置。
       - 其他值：将供应商 ID 与对应模型名拼接。
    3. 内置供应商的 ``base_url`` 中的 ``{accessToken}`` 占位会被替换为当前
       登录 token；其他占位（如 ``{teamId}``）保留原样由上游处理。

    Args:
        db: 数据库会话。
        input_args: task.input_args 的可变副本。
        current_user: 当前认证用户。
        access_token: 当前登录 token，用于替换内置供应商 URL 中的占位。

    Returns:
        处理后的 *input_args* 字典。
    """
    from app.models import LLMProvider
    from app.services.user_default_model_service import get_user_default_model

    input_args["providers"] = []
    providers = db.exec(
        select(LLMProvider).where(
            or_(
                LLMProvider.user_id == current_user.id,
                LLMProvider.is_builtin.is_(True) & LLMProvider.visible_to_all.is_(True),  # type: ignore[union-attr]
            ),
        ),
    ).all()

    provider_configs: list[dict] = []
    provider_configs_map: dict[str, dict] = {}
    for p in providers:
        base_url = p.base_url
        if p.is_builtin and base_url and access_token:
            base_url = base_url.replace("{accessToken}", access_token)
        models_list = [m.strip() for m in p.model.split(";") if m.strip()]
        for model_name in models_list:
            model_data = {
                "name": f"{p.id}{model_name}",
                "type": p.type,
                "api_key": p.api_key,
                "auth_token": p.auth_token,
                "base_url": base_url,
                "model": model_name,
                "temperature": p.temperature,
                "max_tokens": p.max_tokens,
                "timeout": p.timeout,
                "max_retries": p.max_retries,
            }
            provider_configs.append(model_data)
            provider_configs_map[f"{p.id}{model_name}"] = model_data
    # 添加mock供应商
    mock_data = {
        "name": "mock",
        "type": "mock",
        "api_key": "",
        "auth_token": "",
        "base_url": "",
        "model": "mock",
        "temperature": 0.7,
        "max_tokens": 32768,
        "timeout": 60,
        "max_retries": 3,
    }
    provider_configs.append(mock_data)
    provider_configs_map["mock"] = mock_data

    planner_config = input_args.get("planner", {})
    coder_config = input_args.get("coder", {})

    planner_provider = planner_config.get("provider", "default")
    planner_model = planner_config.get("provider_model", "")
    coder_provider = coder_config.get("provider", "default")
    coder_model = coder_config.get("provider_model", "")

    need_defaults = (
        (not planner_provider or planner_provider == "default")
        or (not coder_provider or coder_provider == "default")
    )
    defaults = get_user_default_model(db, current_user.id) if need_defaults else None

    if not planner_provider or planner_provider == "default":
        if defaults and defaults.planner_provider_id and defaults.planner_model_name:
            planner_config["provider"] = f"{defaults.planner_provider_id}{defaults.planner_model_name}"
        else:
            raise HTTPException(
                status_code=400,
                detail="未配置默认 Planner 供应商，请先在用户设置中配置",
            )
    else:
        planner_config["provider"] = f"{planner_provider}{planner_model}"

    if not coder_provider or coder_provider == "default":
        if defaults and defaults.coder_provider_id and defaults.coder_model_name:
            coder_config["provider"] = f"{defaults.coder_provider_id}{defaults.coder_model_name}"
        else:
            raise HTTPException(
                status_code=400,
                detail="未配置默认 Coder 供应商，请先在用户设置中配置",
            )
    else:
        coder_config["provider"] = f"{coder_provider}{coder_model}"

    planner_config.pop("provider_model", None)
    coder_config.pop("provider_model", None)

    # 按需追加实际用到的 provider configs（按 name 去重，避免 planner 与 coder 使用同一 provider 时重复添加）
    seen_provider_names: set[str] = set()
    for name in (planner_config.get("provider"), coder_config.get("provider")):
        if name and name in provider_configs_map and name not in seen_provider_names:
            seen_provider_names.add(name)
            input_args["providers"].append(provider_configs_map[name])
    input_args["planner"] = planner_config
    input_args["coder"] = coder_config
    # 运行强制使用默认的 embedding 模型（未配置 JINA_API_KEY 时不传 api_key）
    embedding_kwargs: dict = {
        "type": "openai_compatible",
        "base_url": "https://api.jinaai.cn/v1",
        "model": "jina-embeddings-v4",
        "dim": 2048,
        "embedding_func_max_async": 2,
    }
    if settings.JINA_API_KEY:
        embedding_kwargs["api_key"] = settings.JINA_API_KEY
    input_args["embedding"] = EmbeddingConfig(**embedding_kwargs).model_dump()
    return input_args


def run_task(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    access_token: str | None = None,
) -> schemas.TaskRunResponse:
    """运行任务：准备运行目录、从 S3 下载数据、提交 Celery 任务。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户
        access_token: 当前登录 token，用于替换内置供应商 URL 中的占位

    Returns:
        任务运行提交响应

    Raises:
        HTTPException: 任务正在运行（409）、数据缺失（404）或下载失败（404）
    """
    task = get_task_with_auth(db, task_id, current_user)

    if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
        raise HTTPException(status_code=409, detail="任务正在运行中，请勿重复提交")

    # 解析供应商列表及 evolution 中的供应商引用
    input_args = dict(task.input_args) if task.input_args else {}
    input_args = _resolve_providers(db, input_args, current_user, access_token)

    # 准备运行参数
    container_name = f"code_user-{current_user.id}"
    user_home = f"{settings.DOCKER_PROJECT_HOME}{container_name}/"
    run_dir = f"{user_home}{task_id}/"

    input_args["project_name"] = "llm4ad"
    input_args["base_dir"] = "/task/data/"
    input_args["run_id"] = "run"
    task_args = {
        "task_id": task_id,
        "project_id": task.project_id,
        "user_id": current_user.id,
        "user_home": user_home,
        "container_name": container_name,
        "run_dir": run_dir,
        "run_args": input_args,
    }

    if not task.input_data_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="未包含数据，请上传数据再试！")

    task_args["input_data_path"] = task.input_data_path

    from app.core.redis import delete_task_logs, push_log_entry

    # 先更新任务 model：清空旧日志、队列，更新状态
    delete_task_logs(str(task.id))

    from sqlmodel import delete

    from app.models import TaskLog

    db.exec(delete(TaskLog).where(TaskLog.task_id == task.id))
    task.status = TaskStatus.PENDING
    # 清空上一次运行残留的报告与结果渲染缓存，避免与新一轮的产物错配
    task.reports = None
    task.result_render = None
    task.updated_time = datetime.now(UTC)
    db.add(task)
    db.commit()

    push_log_entry(
        str(task.id),
        {
            "type": "status",
            "status": TaskStatus.PENDING.value,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )

    # 再提交 Celery 异步任务
    celery_result = run_evolution.delay(task_args)
    task.celery_task_id = celery_result.id
    db.add(task)
    db.commit()
    db.refresh(task)

    return schemas.TaskRunResponse(
        task_id=task.id,
        celery_task_id=celery_result.id,
        status=task.status,
    )


def _force_stop_celery_task(db: Session, task: models.Task, *, reason: str | None = None) -> None:  # noqa: ARG001
    """中止 Celery 任务、强制停止其容器，并同步持久化 Redis 日志。

    为了让停止接口快速响应（亚秒级），本函数：

    1. 先把可选的中断说明日志推送到 Redis；
    2. 通过 Celery abort/revoke 通知 worker 停止任务；
    3. 使用 ``SIGKILL`` 立即终止任务容器（不等优雅退出）；
    4. **同步**调用 :func:`app.tasks.evolution._finalize_task`，把 Redis
       中的运行日志持久化到 DB 并写入 ``FAILED`` 终态。

    第 4 步保证调用方在收到响应时，Redis 日志已经落库；同时由于
    ``_finalize_task`` 通过任务终态做幂等检查，worker 端的 finally
    再次调用时会被短路，不会重复写入。

    Args:
        db: 数据库会话（保留以兼容调用方签名，本函数当前不使用）。
        task: Task 模型实例（必须处于 PENDING 或 RUNNING 状态）。
        reason: 可选的中断原因描述；不为空时作为 error 日志推送到 Redis。
    """
    from app.core.redis import push_log_entry
    from app.tasks.evolution import _finalize_task

    if reason:
        push_log_entry(
            str(task.id),
            {
                "type": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "error_type": "TaskInterrupted",
                "error_message": reason,
            },
        )

    if task.celery_task_id:
        if settings.TASK_CONTAINER_ENABLE:
            from celery.contrib.abortable import AbortableAsyncResult

            AbortableAsyncResult(task.celery_task_id, app=celery_app).abort()
        else:
            celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")

    if settings.TASK_CONTAINER_ENABLE:
        try:
            from app.services.container_service import kill_task_container

            kill_task_container(str(task.id))
        except Exception as e:
            logger.warning(f"强制停止任务容器失败: {e}")

    if task.celery_task_id:
        _finalize_task(task.celery_task_id, TaskStatus.FAILED)


def stop_task(db: Session, task_id: uuid.UUID, current_user: models.User) -> models.Task:
    """停止正在运行或等待中的任务。

    返回前会同步完成：abort Celery 任务、SIGKILL 任务容器、把 Redis 中
    的日志持久化到 DB 并把任务状态置为 ``FAILED``。Worker 端 finally
    再次调用 finalize 时会因终态短路，不会重复写入。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户

    Returns:
        最新任务对象（状态已为 ``FAILED``，运行日志已落 DB）。

    Raises:
        HTTPException: 任务不存在（404）、无权访问（403）或当前状态不可停止（409）
    """
    task = get_task_with_auth(db, task_id, current_user)

    if task.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
        raise HTTPException(status_code=409, detail="当前任务状态无法停止")

    _force_stop_celery_task(db, task, reason=f"任务 {task_id} 已被用户 {current_user.id} 手动停止")
    db.refresh(task)

    logger.info(f"任务 {task_id} 已被用户 {current_user.id} 手动停止")
    return task


def delete_task(db: Session, task_id: uuid.UUID, current_user: models.User) -> Message:
    """删除任务及其关联的 S3 数据。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户

    Returns:
        成功消息

    Raises:
        HTTPException: 任务处于 PENDING/RUNNING 状态时（409）需先停止任务。
    """
    task = get_task_with_auth(db, task_id, current_user)

    if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail="任务正在运行中，请先停止任务再删除",
        )

    if task.input_data_path:
        try:
            keys = storage.list_objects(prefix=task.input_data_path)
            for key in keys:
                storage.delete(key)
        except Exception as e:
            logger.warning(f"清理任务 {task_id} 存储数据失败: {e}")

    db.delete(task)
    db.commit()
    return Message(message="任务已删除")


def get_task_result(db: Session, task_id: uuid.UUID, current_user: models.User) -> schemas.TaskResultResponse:
    """获取 Celery 执行结果，并将状态同步回数据库。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户

    Returns:
        任务执行结果响应
    """
    task = get_task_with_auth(db, task_id, current_user)

    # 未提交过 Celery 任务
    if not task.celery_task_id:
        return schemas.TaskResultResponse(
            task_id=task.id,
            celery_task_id=None,
            celery_status="NOT_DISPATCHED",
            status=task.status,
            result=None,
            error=None,
        )

    async_result = AsyncResult(task.celery_task_id, app=celery_app)
    celery_state = async_result.state

    # 映射 Celery 状态并同步到数据库
    mapped_status = CELERY_STATUS_MAP.get(celery_state, task.status)
    if mapped_status != task.status:
        task.status = mapped_status
        task.updated_time = datetime.now(UTC)
        db.add(task)
        db.commit()
        db.refresh(task)

    # 提取结果或错误信息
    result = None
    error = None
    if async_result.successful():
        result = async_result.result
    elif async_result.failed():
        error = str(async_result.result)

    return schemas.TaskResultResponse(
        task_id=task.id,
        celery_task_id=task.celery_task_id,
        celery_status=celery_state,
        status=task.status,
        result=result,
        error=error,
    )


def upload_task_data(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    files: list[UploadFile],
) -> Message:
    """批量上传任务数据文件到 S3。

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户
        files: 上传的文件列表

    Returns:
        上传成功的消息

    Raises:
        HTTPException: 未上传文件（400）
    """
    task = get_task_with_auth(db, task_id, current_user)

    if not files:
        raise HTTPException(status_code=400, detail="至少上传一个文件")
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="单次上传文件数量不能超过 100 个")

    total_upload_size = 0
    for f in files:
        f.file.seek(0, 2)
        size = f.file.tell()
        f.file.seek(0)
        _check_file_size(size)
        total_upload_size += size

    # 生成存储目录：tasks/{task_id}/{timestamp}
    ts = int(datetime.now(UTC).timestamp())
    prefix = f"tasks/{task_id}/{ts}"

    # upload_task_data 会创建全新前缀，但需检查是否超出总限制
    _check_storage_quota(prefix, total_upload_size)

    storage.ensure_bucket()
    storage.upload_files(
        prefix=prefix,
        files=[(f.filename, f.file, f.content_type) for f in files],
    )

    # 更新任务的数据路径
    task.input_data_path = prefix
    task.updated_time = datetime.now(UTC)
    db.add(task)
    db.commit()

    return Message(message=f"上传成功，共 {len(files)} 个文件")


# ---- 文件管理 ----


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



# 占位文件名：用于在对象存储中标记空文件夹的存在
PLACEHOLDER_NAME = ".keep"


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


_MAX_FILE_BYTES = settings.TASK_MAX_FILE_SIZE_MB * 1024 * 1024
_MAX_STORAGE_BYTES = settings.TASK_MAX_STORAGE_MB * 1024 * 1024


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


def get_task_data_tree(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
) -> schemas.FileTreeResponse:
    """获取任务输入数据的目录树。"""
    task, prefix = _get_task_input_data_path(db, task_id, current_user)
    keys = storage.list_objects(prefix=prefix)
    tree = _build_file_tree(keys, prefix)
    return schemas.FileTreeResponse(tree=tree)


def get_task_data_file(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    file_path: str,
) -> schemas.FileContentResponse:
    """获取任务输入数据中指定文件的文本内容。"""
    _validate_file_path(file_path)
    _reject_placeholder_path(file_path)
    task, prefix = _get_task_input_data_path(db, task_id, current_user)

    key = f"{prefix}/{file_path}".replace("//", "/")
    try:
        data = storage.download(key)
    except Exception:
        raise HTTPException(status_code=404, detail="文件不存在")

    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="该文件不是文本文件，无法读取")

    return schemas.FileContentResponse(file_path=file_path, content=content)


def update_task_data_file(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    file_update: schemas.FileUpdateRequest,
) -> Message:
    """修改任务输入数据中指定文件的内容。

    内容以 UTF-8 写入对象存储；是否允许编辑某类文件由前端决定，后端不再做
    扩展名白名单校验。
    """
    _validate_file_path(file_update.file_path)
    _reject_placeholder_path(file_update.file_path)
    task, prefix = _get_task_input_data_path(db, task_id, current_user)

    key = f"{prefix}/{file_update.file_path}".replace("//", "/")
    new_data = file_update.content.encode("utf-8")
    _check_file_size(len(new_data))
    _check_storage_quota(prefix, len(new_data))
    storage.upload(
        key,
        new_data,
        content_type="text/plain; charset=utf-8",
    )
    return Message(message="文件修改成功")


def delete_task_data_file(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    file_path: str,
) -> Message:
    """删除任务输入数据中的指定文件。"""
    _validate_file_path(file_path)
    _reject_placeholder_path(file_path)
    task, prefix = _get_task_input_data_path(db, task_id, current_user)

    key = f"{prefix}/{file_path}".replace("//", "/")
    # 验证文件确实存在
    existing_keys = storage.list_objects(prefix=key)
    if key not in existing_keys:
        raise HTTPException(status_code=404, detail="文件不存在")

    storage.delete(key)

    _backfill_empty_parent(prefix, file_path)

    return Message(message="文件删除成功")


def rename_task_data_file(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    file_rename: schemas.FileRenameRequest,
) -> Message:
    """重命名任务输入数据中的指定文件（S3 层面为 copy + delete）。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        file_rename: 重命名请求，包含原路径和新路径。

    Returns:
        操作成功的消息。

    Raises:
        HTTPException: 路径非法、源文件不存在或目标文件已存在。
    """
    _validate_file_path(file_rename.old_path)
    _validate_file_path(file_rename.new_path)
    _reject_placeholder_path(file_rename.old_path)
    _reject_placeholder_path(file_rename.new_path)
    task, prefix = _get_task_input_data_path(db, task_id, current_user)

    old_key = f"{prefix}/{file_rename.old_path}".replace("//", "/")
    new_key = f"{prefix}/{file_rename.new_path}".replace("//", "/")

    if old_key == new_key:
        return Message(message="文件名未变更")

    case_only_rename = old_key.lower() == new_key.lower()

    # 校验源文件存在
    existing_keys = storage.list_objects(prefix=old_key)
    if old_key not in existing_keys:
        raise HTTPException(status_code=404, detail="源文件不存在")

    # 校验目标路径不存在；case-only rename 时源/目标在 case-insensitive 后端是同一对象，
    # list 会返回源自身，跳过避免误报
    if not case_only_rename:
        target_keys = storage.list_objects(prefix=new_key)
        if new_key in target_keys:
            raise HTTPException(status_code=409, detail="目标路径已存在同名文件")

    # copy + delete
    bucket = storage.default_bucket
    if case_only_rename:
        # 仅大小写变化：部分 S3 兼容存储底层为 case-insensitive 文件系统，
        # 直接 copy + delete 会作用在同一个物理对象上导致数据丢失。
        # 先 copy 到唯一临时 key 隔离冲突，再迁回目标 key。
        tmp_key = f"{old_key}.__rename_tmp__.{uuid.uuid4().hex}"
        try:
            storage.client.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": old_key},
                Key=tmp_key,
            )
            storage.delete(old_key)
            storage.client.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": tmp_key},
                Key=new_key,
            )
        finally:
            try:
                storage.delete(tmp_key)
            except Exception:
                logger.exception("清理重命名临时对象失败: %s", tmp_key)
    else:
        storage.client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": old_key},
            Key=new_key,
        )
        storage.delete(old_key)

    # 目标目录若仅含占位文件，移除占位（已有真实文件填充）
    new_parent = file_rename.new_path.rsplit("/", 1)[0] if "/" in file_rename.new_path else ""
    _remove_placeholder_if_present(prefix, new_parent)

    # 源目录若变空，则补占位文件保留空目录结构
    _backfill_empty_parent(prefix, file_rename.old_path)

    return Message(message="文件重命名成功")


_DEFAULT_FILE_CONTENT = '''\
def main():
    print("Hello, World!")


# 可通过一级目录下的 requirements.txt 文件指定依赖。
if __name__ == "__main__":
    main()
'''


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


def create_task_data_file(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    file_create: schemas.FileCreateRequest,
) -> schemas.FileCreateResponse:
    """在任务输入数据存储中创建一个带 hello-world 示例的 Python 文件。

    若任务尚无 ``input_data_path``，会自动创建。
    文件放置在用户指定路径下，文件名自动去重
    （``main.py``、``main_1.py``、``main_2.py``……）。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        file_create: 文件创建请求，包含目标路径。

    Returns:
        包含已创建文件相对路径的响应。
    """
    task = get_task_with_auth(db, task_id, current_user)

    target_dir = _resolve_target_directory(file_create.path)
    if target_dir:
        _validate_file_path(target_dir)

    if not task.input_data_path:
        ts = int(datetime.now(UTC).timestamp())
        prefix = f"tasks/{task_id}/{ts}"
        storage.ensure_bucket()
        task.input_data_path = prefix
        task.updated_time = datetime.now(UTC)
        db.add(task)
        db.commit()
        db.refresh(task)

    prefix = task.input_data_path

    dir_prefix = f"{prefix}/{target_dir}/" if target_dir else f"{prefix}/"
    existing_keys = storage.list_objects(prefix=dir_prefix)
    existing_names: set[str] = set()
    for key in existing_keys:
        relative = key[len(dir_prefix):]
        if "/" not in relative and relative and relative != PLACEHOLDER_NAME:
            existing_names.add(relative)

    base_name = "new_file"
    ext = ".py"
    filename = f"{base_name}{ext}"
    counter = 1
    while filename in existing_names:
        filename = f"{base_name}_{counter}{ext}"
        counter += 1

    relative_path = f"{target_dir}/{filename}" if target_dir else filename
    s3_key = f"{prefix}/{relative_path}"
    storage.upload(s3_key, _DEFAULT_FILE_CONTENT.encode("utf-8"), content_type="text/x-python")

    # 目录已写入真实文件，移除可能存在的占位文件
    _remove_placeholder_if_present(prefix, target_dir)

    return schemas.FileCreateResponse(file_path=relative_path)


_FOLDER_NAME_BASE = "new_folder"

# 新建任务时自动创建的顶级文件夹名称
DEFAULT_TOP_FOLDER_NAME = "code"


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


def _ensure_input_data_prefix(
    db: Session, task: models.Task
) -> str:
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


def create_task_data_folder(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    folder_create: schemas.FolderCreateRequest,
) -> schemas.FolderCreateResponse:
    """在任务输入数据目录树中创建新文件夹。

    通过写入占位文件 ``.keep`` 的方式表达空目录的存在。
    不支持在根目录下创建顶级文件夹，``path`` 必须指向一个已有的父目录。
    若未提供 ``name``，将在父目录下按 ``new_folder``、``new_folder_1``... 自动去重。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        folder_create: 文件夹创建请求，包含父目录路径与目标名称。

    Returns:
        包含已创建文件夹相对路径的响应。
    """
    task = get_task_with_auth(db, task_id, current_user)

    parent_dir = _normalize_dir_path(folder_create.path)
    if not parent_dir:
        raise HTTPException(status_code=400, detail="不支持创建顶级文件夹，请在已有文件夹下创建子目录")
    _validate_file_path(parent_dir)

    prefix = _ensure_input_data_prefix(db, task)

    # 收集父目录直接子项的名称（仅一层），用于命名去重 / 冲突判断
    parent_prefix = f"{prefix}/{parent_dir}/"
    existing_keys = storage.list_objects(prefix=parent_prefix)
    direct_children: set[str] = set()
    for key in existing_keys:
        relative = key[len(parent_prefix):]
        if not relative:
            continue
        first_segment = relative.split("/", 1)[0]
        if first_segment and first_segment != PLACEHOLDER_NAME:
            direct_children.add(first_segment)

    if folder_create.name and folder_create.name.strip():
        name = folder_create.name.strip()
        _validate_folder_name(name)
        if name in direct_children:
            raise HTTPException(status_code=409, detail="同级目录下已存在同名条目")
    else:
        name = _FOLDER_NAME_BASE
        counter = 1
        while name in direct_children:
            name = f"{_FOLDER_NAME_BASE}_{counter}"
            counter += 1

    folder_relative = f"{parent_dir}/{name}"
    placeholder_key = f"{prefix}/{folder_relative}/{PLACEHOLDER_NAME}"
    storage.upload(placeholder_key, b"", content_type="text/plain; charset=utf-8")

    return schemas.FolderCreateResponse(folder_path=folder_relative)


def delete_task_data_folder(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    folder_path: str,
) -> Message:
    """递归删除任务输入数据中的指定文件夹及其所有内容。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        folder_path: 待删除的文件夹相对路径，不可为空。

    Returns:
        操作成功的消息。

    Raises:
        HTTPException: 路径非法、为空或文件夹不存在。
    """
    folder_path = _normalize_dir_path(folder_path)
    if not folder_path:
        raise HTTPException(status_code=400, detail="不允许删除根目录")
    _validate_file_path(folder_path)
    task, prefix = _get_task_input_data_path(db, task_id, current_user)

    folder_prefix = f"{prefix}/{folder_path}/"
    keys = storage.list_objects(prefix=folder_prefix)
    if not keys:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    for key in keys:
        storage.delete(key)

    _backfill_empty_parent(prefix, folder_path)

    return Message(message="文件夹删除成功")


def rename_task_data_folder(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    folder_rename: schemas.FolderRenameRequest,
) -> Message:
    """重命名任务输入数据中的指定文件夹（S3 层面为批量 copy + 批量 delete）。

    由于对象存储 key 不可变，重命名等价于对前缀下所有对象执行 copy 到新前缀再删除旧对象。
    复制采用线程池并发，删除采用 ``DeleteObjects`` 批量接口以减少请求次数。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        folder_rename: 重命名请求，包含原路径和新路径。

    Returns:
        操作成功的消息。

    Raises:
        HTTPException: 路径非法、源文件夹不存在、目标文件夹已存在或目标位于源内部。
    """
    from concurrent.futures import ThreadPoolExecutor

    old_path = _normalize_dir_path(folder_rename.old_path)
    new_path = _normalize_dir_path(folder_rename.new_path)
    if not old_path:
        raise HTTPException(status_code=400, detail="不允许重命名根目录")
    if not new_path:
        raise HTTPException(status_code=400, detail="目标路径不能为空")
    _validate_file_path(old_path)
    _validate_file_path(new_path)
    task, prefix = _get_task_input_data_path(db, task_id, current_user)

    if old_path == new_path:
        return Message(message="文件夹名未变更")

    # 拒绝将目录移动到自身子目录下，避免无限自嵌套
    if new_path == old_path or new_path.startswith(old_path + "/"):
        raise HTTPException(status_code=400, detail="目标路径不能位于源文件夹内部")

    old_prefix = f"{prefix}/{old_path}/"
    new_prefix = f"{prefix}/{new_path}/"
    case_only_rename = old_prefix.lower() == new_prefix.lower()

    # 校验源文件夹存在
    src_keys = storage.list_objects(prefix=old_prefix)
    if not src_keys:
        raise HTTPException(status_code=404, detail="源文件夹不存在")

    # 校验目标父目录存在；同目录 rename（含仅大小写变化）父目录不变，无需校验
    old_parent = old_path.rsplit("/", 1)[0] if "/" in old_path else ""
    new_parent = new_path.rsplit("/", 1)[0] if "/" in new_path else ""
    if old_parent != new_parent:
        if not new_parent:
            raise HTTPException(status_code=400, detail="不支持移动到顶级位置，请指定已有的父目录")
        parent_keys = storage.list_objects(prefix=f"{prefix}/{new_parent}/")
        if not parent_keys:
            raise HTTPException(status_code=404, detail="目标父目录不存在")

    # 校验目标路径下不存在同名条目；case-only rename 时源/目标在 case-insensitive 后端
    # 上是同一对象，list 会返回源自身，跳过避免误报
    if not case_only_rename:
        target_keys = storage.list_objects(prefix=new_prefix)
        if target_keys:
            raise HTTPException(status_code=409, detail="目标路径已存在同名文件夹")

    bucket = storage.default_bucket
    tmp_prefix = (
        f"{old_prefix.rstrip('/')}.__rename_tmp__.{uuid.uuid4().hex}/"
        if case_only_rename
        else None
    )

    def _copy_one(src_key: str) -> str:
        relative = src_key[len(old_prefix):]
        dst_key = f"{new_prefix}{relative}"
        storage.client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": src_key},
            Key=dst_key,
        )
        return dst_key

    def _copy_to_tmp(src_key: str) -> str:
        relative = src_key[len(old_prefix):]
        dst_key = f"{tmp_prefix}{relative}"
        storage.client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": src_key},
            Key=dst_key,
        )
        return dst_key

    def _copy_from_tmp(tmp_key: str) -> str:
        relative = tmp_key[len(tmp_prefix):]
        dst_key = f"{new_prefix}{relative}"
        storage.client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": tmp_key},
            Key=dst_key,
        )
        return dst_key

    if case_only_rename:
        # 仅大小写变化：先中转到唯一临时前缀，避开 case-insensitive 后端冲突。
        tmp_keys: list[str] = []
        try:
            with ThreadPoolExecutor(max_workers=16) as executor:
                tmp_keys = list(executor.map(_copy_to_tmp, src_keys))
            storage.delete_many(src_keys)
            with ThreadPoolExecutor(max_workers=16) as executor:
                list(executor.map(_copy_from_tmp, tmp_keys))
        finally:
            if tmp_keys:
                try:
                    storage.delete_many(tmp_keys)
                except Exception:
                    logger.exception("清理文件夹重命名临时对象失败: %s", tmp_prefix)
    else:
        # 并发复制（同 region 服务端复制，瓶颈在请求往返）
        with ThreadPoolExecutor(max_workers=16) as executor:
            list(executor.map(_copy_one, src_keys))
        # 批量删除源对象
        storage.delete_many(src_keys)

    # 目标父目录若存在占位文件，移除占位（已有真实子目录填充）
    _remove_placeholder_if_present(prefix, new_parent)

    # 源父目录若变空，补占位文件保留目录结构
    _backfill_empty_parent(prefix, old_path)

    return Message(message="文件夹重命名成功")


def has_persisted_logs(db: Session, task_id: uuid.UUID) -> bool:
    """检查任务在 task_log 表中是否存在已持久化的日志条目。"""
    from sqlalchemy import func as sa_func

    from app.models import TaskLog

    return db.exec(select(sa_func.count()).where(TaskLog.task_id == task_id)).one() > 0


def get_task_logs(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    cursor: str | None = None,
    limit: int = 100,
    log_type: str | None = None,
    level: list[str] | None = None,
    message_query: str | None = None,
) -> schemas.TaskLogsResponse:
    """读取任务日志：游标分页，倒序查询。

    游标编码为 base64(timestamp_iso|uuid)，标识上一页最早的一条记录。
    首次请求不传 cursor，返回最新的 limit 条；后续传入 next_cursor 向前翻页。
    返回的 entries 按时间正序排列，方便前端直接渲染。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前认证用户。
        cursor: 分页游标（base64 编码）。
        limit: 每页条数。
        log_type: 按日志类型过滤。
        level: 按日志级别过滤，支持多选。
        message_query: 在消息字段中进行全文检索。

    Returns:
        任务日志游标分页响应。
    """
    from sqlalchemy import func as sa_func

    from app.models import TaskLog

    task = get_task_with_auth(db, task_id, current_user)

    db_count = db.exec(select(sa_func.count()).where(TaskLog.task_id == task.id)).one()

    if db_count > 0:
        if limit == 0:
            return _get_all_task_logs_from_db(db, task, log_type, level, message_query)
        return _get_task_logs_from_db(
            db,
            task,
            cursor,
            limit,
            log_type,
            level,
            message_query,
        )

    if limit == 0:
        return _get_all_task_logs_from_redis(task, log_type, level, message_query)
    return _get_task_logs_from_redis(task, cursor, limit, log_type, level, message_query)


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a cursor string into (timestamp, id)."""
    import base64

    raw = base64.urlsafe_b64decode(cursor).decode()
    ts_str, id_str = raw.rsplit("|", 1)
    ts = datetime.fromisoformat(ts_str)
    return ts, uuid.UUID(id_str)


def _encode_cursor(timestamp: datetime, log_id: uuid.UUID) -> str:
    """Encode (timestamp, id) into an opaque cursor string."""
    import base64

    raw = f"{timestamp.isoformat()}|{log_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _get_all_task_logs_from_db(
    db: Session,
    task: models.Task,
    log_type: str | None,
    level: list[str] | None,
    message_query: str | None,
) -> schemas.TaskLogsResponse:
    """Return all logs from DB without pagination."""
    from app.models import TaskLog
    from app.utils.log_persist import strip_generated_fields_for_list, task_log_to_dict

    query = select(TaskLog).where(TaskLog.task_id == task.id)

    if log_type:
        query = query.where(TaskLog.type == log_type)
    if level:
        query = query.where(TaskLog.level.in_(level))
    if message_query:
        query = query.where(TaskLog.message.contains(message_query))

    query = query.order_by(TaskLog.timestamp.asc(), TaskLog.id.asc())
    rows = list(db.exec(query).all())

    entries = [task_log_to_dict(row) for row in rows]
    for entry in entries:
        strip_generated_fields_for_list(entry)

    return schemas.TaskLogsResponse(
        task_id=task.id,
        source="db",
        entries=entries,
        next_cursor=None,
        has_more=False,
    )


def _filter_redis_entries(
    entries: list[dict],
    log_type: str | None,
    level: list[str] | None,
    message_query: str | None,
) -> list[dict]:
    """对 Redis 中的日志条目按 type/level/message 做内存过滤。"""
    if not entries:
        return entries
    if not log_type and not level and not message_query:
        return entries

    level_set = set(level) if level else None
    result = []
    for entry in entries:
        if log_type and entry.get("type") != log_type:
            continue
        if level_set is not None and entry.get("level") not in level_set:
            continue
        if message_query:
            msg = entry.get("message")
            if not msg or message_query not in msg:
                continue
        result.append(entry)
    return result


def _get_all_task_logs_from_redis(
    task: models.Task,
    log_type: str | None = None,
    level: list[str] | None = None,
    message_query: str | None = None,
) -> schemas.TaskLogsResponse:
    """Return all logs from Redis without pagination."""
    from app.core.redis import read_all_logs
    from app.utils.log_persist import strip_generated_fields_for_list

    all_entries = read_all_logs(task.id)
    filtered = _filter_redis_entries(all_entries or [], log_type, level, message_query)
    for entry in filtered:
        strip_generated_fields_for_list(entry)

    return schemas.TaskLogsResponse(
        task_id=task.id,
        source="redis",
        entries=filtered,
        next_cursor=None,
        has_more=False,
    )


def _get_task_logs_from_db(
    db: Session,
    task: models.Task,
    cursor: str | None,
    limit: int,
    log_type: str | None,
    level: list[str] | None,
    message_query: str | None,
) -> schemas.TaskLogsResponse:
    """Cursor-paginated log retrieval from DB, reverse chronological."""
    from sqlalchemy import tuple_

    from app.models import TaskLog
    from app.utils.log_persist import strip_generated_fields_for_list, task_log_to_dict

    query = select(TaskLog).where(TaskLog.task_id == task.id)

    if log_type:
        query = query.where(TaskLog.type == log_type)
    if level:
        query = query.where(TaskLog.level.in_(level))
    if message_query:
        query = query.where(TaskLog.message.contains(message_query))

    if cursor:
        cursor_ts, cursor_id = _decode_cursor(cursor)
        query = query.where(tuple_(TaskLog.timestamp, TaskLog.id) < tuple_(cursor_ts, cursor_id))

    query = query.order_by(TaskLog.timestamp.desc(), TaskLog.id.desc()).limit(limit + 1)
    rows = list(db.exec(query).all())

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    rows.reverse()

    next_cursor = None
    if has_more and rows:
        oldest = rows[0]
        next_cursor = _encode_cursor(oldest.timestamp, oldest.id)

    entries = [task_log_to_dict(row) for row in rows]
    for entry in entries:
        strip_generated_fields_for_list(entry)

    return schemas.TaskLogsResponse(
        task_id=task.id,
        source="db",
        entries=entries,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def _get_task_logs_from_redis(
    task: models.Task,
    cursor: str | None,
    limit: int,
    log_type: str | None = None,
    level: list[str] | None = None,
    message_query: str | None = None,
) -> schemas.TaskLogsResponse:
    """Cursor-paginated log retrieval from Redis, reverse chronological."""
    import base64

    from app.core.redis import read_all_logs
    from app.utils.log_persist import strip_generated_fields_for_list

    all_entries = read_all_logs(task.id)
    all_entries = _filter_redis_entries(all_entries or [], log_type, level, message_query)

    if not all_entries:
        return schemas.TaskLogsResponse(
            task_id=task.id,
            source="redis",
            entries=[],
            next_cursor=None,
            has_more=False,
        )

    if cursor:
        cursor_idx = int(base64.urlsafe_b64decode(cursor).decode())
    else:
        cursor_idx = len(all_entries)

    start = max(cursor_idx - limit, 0)
    end = cursor_idx
    page = all_entries[start:end]

    for entry in page:
        strip_generated_fields_for_list(entry)

    has_more = start > 0
    next_cursor = None
    if has_more:
        next_cursor = base64.urlsafe_b64encode(str(start).encode()).decode()

    return schemas.TaskLogsResponse(
        task_id=task.id,
        source="redis",
        entries=page,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def get_task_stats(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
) -> schemas.TaskStatsResponse:
    """获取任务的基本统计信息：解的个数、平均分、最高分。

    解从 ``type=generated`` 的日志中提取，分数读取自 ``data.evaluation.score``。
    优先从数据库读取已持久化日志，运行中任务回退到 Redis。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。

    Returns:
        包含解的个数、平均分、最高分的统计响应。
    """
    task = get_task_with_auth(db, task_id, current_user)

    from app.models import TaskLog
    from app.utils.log_persist import task_log_to_dict

    rows = db.exec(select(TaskLog).where(TaskLog.task_id == task.id, TaskLog.type == "generated")).all()
    if rows:
        entries = [task_log_to_dict(row) for row in rows]
    else:
        from app.core.redis import read_all_logs

        entries = [e for e in read_all_logs(task.id) if e.get("type") == "generated"]

    scores: list[float] = []
    for entry in entries:
        data = entry.get("data")
        if not isinstance(data, dict):
            continue
        evaluation = data.get("evaluation")
        if not isinstance(evaluation, dict):
            continue
        score = evaluation.get("score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            scores.append(float(score))

    solution_count = len(entries)
    avg_score = sum(scores) / len(scores) if scores else None
    max_score = max(scores) if scores else None

    return schemas.TaskStatsResponse(
        task_id=task.id,
        solution_count=solution_count,
        avg_score=avg_score,
        max_score=max_score,
        input_args=task.input_args or {},
        created_time=task.created_time,
        updated_time=task.updated_time,
    )


def get_config_schema(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
) -> schemas.AppConfigSchemaResponse:
    """获取配置的schema，用于前端生成表单

    Args:
        db: 数据库会话
        task_id: 任务 ID
        current_user: 当前登录用户

    Returns:
        返回配置的schema

    """
    # TODO 可根据任务进行动态识别不同的schema
    get_task_with_auth(db, task_id, current_user)
    return schemas.AppConfigSchemaResponse(config_schema=AppConfig.model_json_schema())


def generate_result_render(
    db: Session,
    task_id: uuid.UUID,
    current_user: models.User,
    request: "ResultRenderGenerateRequest",
) -> "ResultRenderGenerateResponse":
    """生成任务结果渲染数据。

    若 task.result_render 中已存在该类型的已完成结果，直接返回缓存数据。
    否则调用生成逻辑并将结果持久化到 result_render 字段。

    Args:
        db: 数据库会话。
        task_id: 任务 ID。
        current_user: 当前登录用户。
        request: 结果渲染生成请求。

    Returns:
        ResultRenderGenerateResponse: 包含状态和结果数据的响应。
    """
    from sqlalchemy.orm.attributes import flag_modified

    from app.schemas.result_render import (
        ResultRenderGenerateResponse,
        ResultRenderStatus,
    )

    task = get_task_with_auth(db, task_id, current_user)
    rt = request.result_type.value
    cache_key = f"{rt}_{request.language}_{request.theme}"

    existing = (task.result_render or {}).get(cache_key)
    if not request.force and existing and existing.get("status") == ResultRenderStatus.COMPLETED:
        return ResultRenderGenerateResponse(
            task_id=task.id,
            result_type=request.result_type,
            status=ResultRenderStatus.COMPLETED,
            message="结果已存在，直接返回缓存",
            data=existing.get("data"),
        )

    try:
        from llm4ad.frontend.visualization import VisualizationAPI

        container_name = f"code_user-{current_user.id}"
        user_home = f"{settings.DOCKER_PROJECT_HOME}{container_name}/"
        run_dir = f"{user_home}{task_id}/"
        result_dir = f"{run_dir}llm4ad/run/"
        data = VisualizationAPI(
            generated_dir=f"{result_dir}generated", embedding_dir=f"{result_dir}embedding"
        ).generate_evaluation_trace_echarts_config(dark_mode=request.theme == "dark")
    except Exception as e:
        logger.error(f"生成结果渲染失败: task_id={task_id}, type={rt}, error={e}")
        return ResultRenderGenerateResponse(
            task_id=task.id,
            result_type=request.result_type,
            status=ResultRenderStatus.FAILED,
            message=f"生成失败: {e}",
            data=None,
        )

    render_dict = task.result_render or {}
    render_dict[cache_key] = {
        "status": ResultRenderStatus.COMPLETED,
        "data": data,
    }
    task.result_render = render_dict
    flag_modified(task, "result_render")
    db.add(task)
    db.commit()
    db.refresh(task)

    return ResultRenderGenerateResponse(
        task_id=task.id,
        result_type=request.result_type,
        status=ResultRenderStatus.COMPLETED,
        message="生成成功",
        data=data,
    )


def verify_code_auth(request: Request, db: Session) -> Response:
    """验证 code-server 的 cookie token 并返回带 X-User-ID 头的响应。

    Args:
        request: HTTP 请求对象
        db: 数据库会话

    Returns:
        包含 X-User-ID 头的 200 响应

    Raises:
        HTTPException: 缺少 token（401）、token 无效（401）或用户不存在（401）
    """
    code_token = request.cookies.get("code_token")
    if not code_token:
        raise HTTPException(status_code=401, detail="缺少认证令牌")

    payload = decode_access_token(token=code_token, scope="code")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token无效！")

    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或未启用！")

    # 刷新活跃时间，供后台空闲清理任务判断；失败已在内部记录日志
    touch_code_user_active(user.id)

    # 认证成功，将 user_id 放在响应头中
    response = Response(status_code=200)
    response.headers["X-User-ID"] = str(user.id)
    return response


# ---- Chat Tune 上传接口 ----


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

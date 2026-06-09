# LLM4AD Web — Backend Service

> 基于 FastAPI 的企业级后端服务，为 **LLM4AD（Large Language Model for Algorithm Design）** 平台提供 Web API、任务编排、容器化算法执行、演化分析报告等核心能力。

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.114+-009688.svg)]()
[![License](https://img.shields.io/badge/License-Internal-lightgrey.svg)]()

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [目录结构](#目录结构)
- [快速开始](#快速开始)
- [开发指南](#开发指南)
- [运行与部署](#运行与部署)
- [数据库迁移](#数据库迁移)
- [异步任务与 Worker](#异步任务与-worker)
- [测试](#测试)
- [代码规范](#代码规范)
- [常用脚本](#常用脚本)
- [贡献规范](#贡献规范)

---

## 项目简介

本项目是 LLM4AD 平台的 Web 后端服务，承担以下职责：

- 暴露 RESTful / SSE API 供前端及第三方调用
- 管理项目、任务、Provider、报告等核心业务实体
- 编排 LLM 驱动的算法演化任务，并通过 Docker 容器隔离执行
- 提供基于 RBAC 的统一权限模型与 JWT 认证
- 集成对象存储、消息队列与缓存以支撑高并发任务调度

## 核心特性

| 特性 | 说明 |
|---|---|
| **任务编排** | 基于 Celery + Redis 的异步任务系统，支持长任务、子任务树、断点续跑 |
| **容器化执行** | 算法运行隔离在独立 Docker 容器中，宿主侧 Worker 负责日志中继与状态回写 |
| **流式输出** | 借助 SSE 提供实时日志、报告生成等流式接口 |
| **演化分析报告** | 内置 4 类报告（技术变更 / 节点对比 / 链路分析 / 冠军诞生），支持 LLM 流式生成与协作式取消 |
| **RBAC 权限** | 用户—角色—权限三级模型，路由级声明式鉴权 |
| **多 Provider 抽象** | 统一封装 OpenAI、Anthropic 等 LLM 服务商 |
| **对象存储** | 通过 S3 兼容协议存取数据集与产物 |
| **可观测性** | Loguru 结构化日志 + Sentry 异常监控 + Flower 任务面板 |

## 技术栈

- **Web 框架**：FastAPI（含 Starlette、Pydantic v2）
- **ORM / 数据库**：SQLModel + Alembic + PostgreSQL（psycopg）
- **缓存 / 队列**：Redis、Celery（gevent worker）+ Flower
- **认证**：PyJWT、pwdlib（Argon2 / Bcrypt）
- **容器**：Docker SDK
- **对象存储**：boto3（S3 兼容）
- **LLM 集成**：openai、claude-agent-sdk、内嵌 `llm4ad` 包
- **运维工具**：Typer CLI、Rich、Loguru、Sentry SDK
- **构建工具**：uv、hatchling

## 系统架构

```
┌──────────┐   HTTP / SSE   ┌──────────────────┐   Celery   ┌────────────┐
│ Frontend ├───────────────►│  FastAPI Backend ├───────────►│   Worker   │
└──────────┘                │   (this repo)    │            └─────┬──────┘
                            │                  │                  │ Docker SDK
                            │ ┌──────┬───────┐ │                  ▼
                            │ │ API  │  CRUD │ │           ┌─────────────┐
                            │ ├──────┼───────┤ │           │  Task       │
                            │ │Models│Service│ │           │  Container  │
                            │ └──────┴───────┘ │           │ (llm4ad)    │
                            └────────┬─────────┘           └──────┬──────┘
                                     │                            │
                ┌────────────────────┼────────────────────────────┤
                ▼                    ▼                            ▼
          ┌──────────┐         ┌─────────┐                   ┌─────────┐
          │PostgreSQL│         │  Redis  │                   │   S3    │
          └──────────┘         └─────────┘                   └─────────┘
```

## 目录结构

```
src/backend/
├── app/
│   ├── api/                    # FastAPI 路由层
│   │   ├── base_routes/        # 基础能力（登录、用户、权限、健康检查）
│   │   ├── llm4ad/             # LLM4AD 业务路由（项目/任务/Provider/报告）
│   │   ├── deps.py             # 路由依赖（会话、当前用户、权限校验）
│   │   └── main.py             # 路由聚合
│   ├── core/                   # 基础设施
│   │   ├── celery.py           # Celery 应用与队列配置
│   │   ├── config.py           # Pydantic Settings 全局配置
│   │   ├── db.py               # SQLModel 引擎 / 会话工厂
│   │   ├── redis.py            # Redis 客户端与日志/SSE 工具
│   │   ├── docker.py           # Docker 客户端封装
│   │   ├── storage.py          # S3 对象存储封装
│   │   ├── security.py         # JWT、密码哈希
│   │   └── constants.py        # 常量与枚举
│   ├── crud/                   # 数据访问层（Repository 模式）
│   ├── models/                 # SQLModel ORM 模型
│   ├── schemas/                # Pydantic 请求/响应 Schema
│   ├── services/               # 业务逻辑层
│   ├── tasks/                  # Celery 任务定义（容器执行、演化）
│   ├── utils/                  # 工具函数
│   ├── alembic/                # 数据库迁移脚本
│   ├── email-templates/        # MJML 邮件模板
│   ├── backend_pre_start.py    # 启动前数据库连通性检查
│   └── main.py                 # FastAPI 应用入口
├── scripts/                    # 运维脚本
├── tests/                      # 单元 / 集成测试
├── cli.py                      # Typer CLI 入口
├── alembic.ini                 # Alembic 配置
├── Dockerfile                  # 后端服务镜像
├── Dockerfile.task             # 任务运行镜像
└── pyproject.toml              # 项目元信息与工具配置
```

## 快速开始

### 环境要求

| 组件 | 版本 |
|---|---|
| Python | ≥ 3.12 |
| PostgreSQL | ≥ 14 |
| Redis | ≥ 6 |
| Docker | ≥ 24（任务容器化执行所需）|
| uv | 最新版（依赖管理）|

### 安装依赖

```sh
# 同步依赖（含开发依赖）
uv sync

# 激活虚拟环境
source .venv/bin/activate          # Linux / macOS
.venv\Scripts\activate             # Windows
```

### 配置环境变量

在项目根目录创建 `.env`，至少包含以下配置（示例）：

```dotenv
PROJECT_NAME=LLM4AD
ENVIRONMENT=local
SECRET_KEY=<replace-with-strong-secret>

# Database
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=llm4ad
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# Object Storage (S3-compatible)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=llm4ad

# Superuser
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=<replace>
```

### 初始化数据库

```sh
# 应用迁移
alembic upgrade head

# 创建超级管理员
python cli.py data create-superuser
```

### 启动开发服务器

```sh
fastapi run --reload app/main.py
```

服务默认监听 `http://localhost:8000`，Swagger 文档位于 `/docs`。

## 开发指南

### 编码约定

- **注释规范**：所有公共模块、类、函数必须使用 **Google 风格中文 docstring**；行内注释一律中文
- **类型注解**：强制启用，遵循 PEP 604（`X | None`）与 PEP 585 泛型
- **代码格式**：black（行宽 120）+ isort + ruff
- **提交规范**：

  ```
  (feat|fix|ref): 标题

  1. 变更点 1
  2. 变更点 2
  ```

  - `feat`：新增特性
  - `fix`：缺陷修复
  - `ref`：重构

### 分层职责

| 层 | 职责 | 禁止事项 |
|---|---|---|
| `api/` | 参数校验、路由分发、依赖注入 | 不写业务逻辑、不直接操作 ORM |
| `services/` | 业务编排、跨实体协作 | 不直接处理 HTTP 状态码（除少量 HTTPException） |
| `crud/` | 单实体的增删改查 | 不写跨实体的复杂业务 |
| `models/` | ORM 模型与表关系 | 不放业务方法 |
| `schemas/` | 请求/响应的 Pydantic 模型 | 不依赖 ORM 模型 |

## 运行与部署

### 容器构建

```sh
# 构建后端服务镜像
docker build -f src/backend/Dockerfile -t llm4ad-backend:latest .

# 构建任务运行镜像（被 Backend 调度执行 LLM4AD 任务）
docker build -f src/backend/Dockerfile.task -t llm4ad-task-runner:latest .
```

> **重要**：`llm4ad-task-runner` 镜像必须在宿主机上预先构建，Backend 会在创建任务容器时引用该镜像。

### 生产启动

```sh
fastapi run app/main.py --host 0.0.0.0 --port 8000 --workers 4
```

## 数据库迁移

```sh
# 根据模型变更生成迁移脚本
alembic revision --autogenerate -m "Add column last_name to user"

# 应用迁移
alembic upgrade head

# 回滚一次迁移
alembic downgrade -1
```

> 修改 `app/models/` 后必须生成迁移，禁止直接在数据库手动修改 schema。

## 异步任务与 Worker

### 启动 Celery Worker

```sh
# Linux / macOS（推荐 prefork 或 gevent）
celery -A app.core.celery worker --loglevel=info

# Windows调试时推荐用threads，兼容性最好，支持并发
celery -A app.core.celery worker --loglevel=info -P threads --concurrency=2

# 本地调试单进程
celery -A app.core.celery worker --loglevel=info -P solo
```

### Flower 监控面板

```sh
celery -A app.core.celery flower --port=5555
```

访问 `http://localhost:5555` 查看任务队列、Worker 状态与历史。

## 测试

```sh
# 全量测试
pytest

# 覆盖率报告
pytest --cov=app --cov-report=html

# 仅单元测试
pytest -m unit

# 仅集成测试
pytest -m integration

# 指定文件
pytest tests/path/to/test_file.py::test_function_name
```

## 代码规范

```sh
# 格式化
black src/ tests/
isort src/ tests/

# Lint（自动修复）
ruff check src/ tests/ --fix

# 类型检查
mypy src/
```

> **提交前**请务必执行：
> ```sh
> uv run --python 3.12 ruff check app/
> ```
> 并修复其报告的问题。

## 常用脚本

| 命令 | 说明 |
|---|---|
| `python cli.py data create-superuser` | 创建或重置超级管理员账号 |
| `python cli.py --help` | 查看 CLI 帮助 |
| `alembic upgrade head` | 应用所有数据库迁移 |
| `alembic revision --autogenerate -m "..."` | 生成新迁移脚本 |
| `fastapi run --reload app/main.py` | 启动开发服务器 |
| `celery -A app.core.celery worker -P gevent` | 启动异步任务 Worker |
| `celery -A app.core.celery flower --port=5555` | 启动任务监控面板 |

### 邮件模板

`app/email-templates/` 中的 MJML 模板使用 [MJML VSCode 扩展](https://github.com/mjmlio/vscode-mjml) 进行可视化编辑与导出 HTML。

## 贡献规范

1. 从 `master` 切出特性分支：`feat/<topic>` / `fix/<topic>` / `ref/<topic>`
2. 提交前完成：`black` + `isort` + `ruff` + `mypy` + `pytest`
3. PR 描述需包含变更动机、影响范围与测试方式
4. 涉及数据库变更必须附带 Alembic 迁移脚本
5. 涉及配置变更必须同步更新 `.env.example` 与本 README

---

如有问题请联系项目维护者，或在内部 Issue 系统提交工单。

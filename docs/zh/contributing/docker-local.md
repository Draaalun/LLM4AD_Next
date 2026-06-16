# Docker 本地启动

本文说明贡献者常用的 Docker 工作流。开发 Web UI、调试部署栈，或需要 Python CLI 之外的平台基础服务时，可以从这里开始。

## 选择启动模式

| 模式 | 命令 | 适用场景 |
|---|---|---|
| 本地基础设施 | `./dev.sh infra` 或 `.\dev.ps1 infra` | 后端和前端在宿主机运行，只把 PostgreSQL、Redis、RustFS、mailcatcher、code-server proxy 放进 Docker。日常开发推荐这个模式。 |
| 完整本地栈 | `./dev.sh full` 或 `.\dev.ps1 full` | 用 Docker 从本地源码构建并运行 backend、worker、frontend 和基础设施。适合调试部署行为。 |
| 镜像部署 | `./start.sh --debug` | 运行已经发布的部署镜像，并额外暴露调试端口。适合发布验证。 |

所有命令都在 `docker/` 目录下执行。

## 前置依赖

- Docker Engine 和 Compose 插件（`docker compose version`）
- 足够的本地磁盘空间，用于 PostgreSQL、Redis、RustFS、backend、frontend、task-runner 镜像
- 一个可读写的项目工作目录，用于存放生成的用户项目

Linux 下后端会挂载 `/var/run/docker.sock`，以便任务启动隔离运行容器。请确保当前用户有 Docker 访问权限。

## 安装 Docker

本项目使用 Docker Compose v2，也就是 `docker compose` 命令。安装后先验证：

```bash
docker version
docker compose version
```

### Windows：Docker Desktop

本地开发推荐使用 [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)。

1. 确认 Windows 满足 Docker Desktop 当前系统要求。
2. 如果尚未启用 WSL 2，请先在 Windows 中启用 WSL 2。
3. 下载并运行 `Docker Desktop Installer.exe`。
4. 除非组织要求安装给所有用户，否则使用 per-user 安装模式。
5. 安装器询问 backend 时，选择 **Use WSL 2 instead of Hyper-V**。
6. 从开始菜单启动 Docker Desktop，并接受 Docker Desktop 条款。
7. 打开 PowerShell 验证：

```powershell
docker version
docker compose version
```

使用本项目的 `.\dev.ps1 ...` 时，Docker Desktop 需要保持运行。请使用 WSL 2 提供的 Linux containers；当前本地 compose 栈不支持 Windows containers。

Docker Desktop 在公司环境中的授权取决于组织类型和规模。企业使用前请以官方安装页中的当前订阅条款为准。

### macOS：Docker Desktop

安装 [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)，从 `/Applications` 启动 Docker Desktop，接受 Docker Desktop 条款后验证：

```bash
docker version
docker compose version
```

### Linux：Docker Engine

按发行版安装 [Docker Engine](https://docs.docker.com/engine/install/)。如果包源没有自动安装 Compose v2，再安装 [Docker Compose plugin](https://docs.docker.com/compose/install/)。

安装后确认当前 shell 可以访问 Docker：

```bash
docker version
docker compose version
```

如果 `docker version` 报权限错误，可以用 `sudo` 运行 Docker 命令，或按 Docker 官方 post-installation 步骤配置非 root 访问。

## 创建 `.env`

复制本地示例配置并修改必填项：

```bash
cd docker
cp .env.develop.local.example .env
```

Windows PowerShell：

```powershell
cd docker
Copy-Item .env.develop.local.example .env
```

启动服务前至少设置这些变量：

| 变量 | 用途 |
|---|---|
| `SECRET_KEY` | 应用密钥。可用 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成。 |
| `PROVIDER_ENCRYPTION_KEY` | 已保存 Provider 凭据的稳定加密密钥。生成方式相同，不要随意轮换。 |
| `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD` | 初始管理员账号。 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码。 |
| `REDIS_PASSWORD` | Redis 密码。 |
| `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` | RustFS 对象存储凭据。 |
| `HOST_PROJECT_HOME` / `DOCKER_PROJECT_HOME` | 宿主机与容器内项目工作目录。本地调试时建议使用相同绝对路径。 |

如果后端在宿主机运行，基础服务地址保持 localhost：

```dotenv
POSTGRES_SERVER=localhost
REDIS_HOST=localhost
RUSTFS_ENDPOINT=http://localhost:9000
AUTH_BACKEND_URL=http://host.docker.internal:8000
FRONTEND_HOST=http://localhost:5173
CHAT_TUNE_CONTAINER_NETWORK=false
```

## 本地基础设施模式

只启动基础设施服务：

```bash
cd docker
./dev.sh infra
```

Windows PowerShell：

```powershell
cd docker
.\dev.ps1 infra
```

该模式使用 `compose.yml` 和 `compose.override.yml`。override 会暴露基础设施端口，并禁用应用容器，方便你在宿主机直接运行后端和前端。

暴露的服务：

| 服务 | 地址 / 端口 |
|---|---|
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| RustFS API | `http://localhost:9000` |
| RustFS 控制台 | `http://localhost:9001` |
| Adminer | `http://localhost:8080` |
| Mailcatcher UI | `http://localhost:1081` |
| Mailcatcher SMTP | `localhost:1025` |
| Code-server proxy | `http://localhost:8083` |

然后在宿主机启动后端：

```bash
cd ../src/backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

测试异步任务时，在另一个终端启动 worker：

```bash
cd ../src/backend
uv run celery -A app.core.celery worker --loglevel=info --concurrency=2
```

启动前端：

```bash
cd ../src/frontend
bun install
bun run dev
```

后端默认读取 `../../docker/.env`，因此后端相关命令建议从 `src/backend` 执行。

## 完整本地栈模式

用本地源码构建并启动完整栈，同时暴露调试端口：

```bash
cd docker
./dev.sh full
```

Windows PowerShell：

```powershell
cd docker
.\dev.ps1 full
```

该模式使用 `compose.yml` 和 `compose.deploy.debug.yml`，并启用 `debug` profile。它会在 Docker 中运行 backend、worker、frontend、基础设施、Adminer 和 Flower。

常用入口：

| 服务 | 地址 / 端口 |
|---|---|
| Frontend | `http://localhost:${FRONTEND_PORT}`；`.env` 示例默认是 `18041` |
| Backend API | `http://localhost:8000` |
| Adminer | `http://localhost:8080` |
| Flower | `http://localhost:5555` |
| RustFS 控制台 | `http://localhost:9001` |

查看日志：

```bash
./dev.sh logs
./dev.sh logs backend worker
```

Windows PowerShell：

```powershell
.\dev.ps1 logs
.\dev.ps1 logs backend worker
```

查看服务状态：

```bash
./dev.sh ps
```

Windows PowerShell：

```powershell
.\dev.ps1 ps
```

## 镜像部署调试模式

如果要使用已经发布的部署镜像，而不是本地构建镜像，请使用 `start.sh`：

```bash
cd docker
TAG=v1.0.0 ./start.sh start --debug
```

`--debug` 会引入 `compose.deploy.debug.yml`，启用 `debug` profile，并暴露 PostgreSQL、Redis、RustFS、backend、Adminer 和 Flower 端口。

## 停止与清理

停止容器但保留容器：

```bash
./dev.sh stop
```

Windows PowerShell：

```powershell
.\dev.ps1 stop
```

移除 compose 容器和孤儿容器，但保留 `docker/app-data/` 下的绑定挂载数据：

```bash
./dev.sh remove
```

Windows PowerShell：

```powershell
.\dev.ps1 remove
```

镜像部署模式使用：

```bash
./start.sh stop --debug
./start.sh remove --debug
```

## 常见问题

| 现象 | 可能原因 | 解决 |
|---|---|---|
| `Missing docker/.env` | 尚未创建本地环境文件 | 在 `docker/` 下运行 `cp .env.develop.local.example .env`，并修改必填项。 |
| Compose 报 `Variable not set` | 必填密钥仍为空 | 补齐 `.env` 中所有必填变量。 |
| 后端连不上 DB 或 Redis | 后端在宿主机运行，但 `.env` 仍指向 Docker 服务名 | 使用 `POSTGRES_SERVER=localhost` 和 `REDIS_HOST=localhost`。 |
| 重启后已保存的 Provider 凭据消失 | `PROVIDER_ENCRYPTION_KEY` 变化或为空 | 设置稳定的 `PROVIDER_ENCRYPTION_KEY`，并对同一个数据库保持不变。 |
| 任务容器访问不到生成文件 | `HOST_PROJECT_HOME` 与 `DOCKER_PROJECT_HOME` 不符合本地路径预期 | 本地调试时使用相同绝对路径，并确保目录存在。 |
| 端口已被占用 | 调试端口被其他进程使用 | 修改 `.env` 中对应端口，或停止冲突进程。 |

## 相关文档

- [开发环境](development.md)
- [贡献指南](guidelines.md)
- [Web UI 概览](../web-ui/overview.md)

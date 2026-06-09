# docker部署

## 使用

### 配置

首次部署请复制示例文件并按需修改：

```bash
cp .env.develop.local.example .env
```

`.env` 中以下变量**必须**显式配置（未设置时 compose 会直接报错或服务无法正常工作）：

**安全密钥**

- `SECRET_KEY`：应用密钥，可通过 `python -c "import secrets; print(secrets.token_urlsafe(32))"` 生成
- `PROVIDER_ENCRYPTION_KEY`：供应商凭据加密专用密钥，务必显式设置且设置后不要再变更（留空会回退到 `SECRET_KEY` 派生，`SECRET_KEY` 轮换后会导致已加密的供应商凭据无法解密）。生成方式同上

**管理员账户**

- `FIRST_SUPERUSER`：首个超级管理员邮箱
- `FIRST_SUPERUSER_PASSWORD`：超管密码，至少 8 位

**基础服务凭据**

- `POSTGRES_PASSWORD`：PostgreSQL 数据库密码
- `REDIS_PASSWORD`：Redis 密码
- `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY`：RustFS 对象存储凭据

**项目目录**

- `HOST_PROJECT_HOME` / `DOCKER_PROJECT_HOME`：项目工作目录挂载路径（本地调试时两者需保持一致；部署时 `HOST_PROJECT_HOME` 可为服务器上任意已存在且可读写的目录）

其余变量（端口、镜像名、SMTP、APT/PyPI 镜像源等）可沿用示例文件中的默认值，完整说明见 `.env.develop.local.example`。

## 使用方式

- 启动指定版本（示例：`v1.0.0`）
```shell
TAG=v1.0.0 ./start.sh start
```

- 启动默认版本（`latest`）
```shell
./start.sh start
```

`start` 是默认命令，也可以直接执行 `./start.sh`。启动脚本会先拉取当前版本所需镜像，以及后端运行时动态容器所需镜像，再启动服务。

- 停止服务和后端动态容器
```shell
./start.sh stop
```

- 移除服务和后端动态容器
```shell
./start.sh remove
```

- 升级到指定版本
```shell
TAG=v1.0.1 ./start.sh upgrade
```

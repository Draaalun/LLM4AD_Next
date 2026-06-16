# Contributing to LLM4AD_Next

Thanks for helping improve LLM4AD_Next. This repository keeps the full contributor guide in the documentation tree:

- English: [Contribution Guidelines](docs/en/contributing/guidelines.md)
- English development setup: [Development Setup](docs/en/contributing/development.md)
- English Docker local startup: [Docker Local Startup](docs/en/contributing/docker-local.md)
- 中文： [贡献指南](docs/zh/contributing/guidelines.md)
- 中文开发环境： [开发环境](docs/zh/contributing/development.md)
- 中文 Docker 本地启动： [Docker 本地启动](docs/zh/contributing/docker-local.md)

## Quick Checklist

1. Fork the repository and branch from `main`.
2. Install dependencies with `uv sync --extra dev,providers,docs`.
3. Use `docker/dev.sh infra` on macOS/Linux or `docker/dev.ps1 infra` on Windows when you need PostgreSQL, Redis, RustFS, mailcatcher, or the code-server proxy for local Web UI work.
4. Keep each pull request focused on one logical change.
5. Run the relevant tests and checks before opening a PR.

## 快速清单

1. Fork 仓库并从 `main` 创建分支。
2. 使用 `uv sync --extra dev,providers,docs` 安装开发依赖。
3. 本地开发 Web UI 需要 PostgreSQL、Redis、RustFS、mailcatcher 或 code-server proxy 时，macOS/Linux 使用 `docker/dev.sh infra`，Windows 使用 `docker/dev.ps1 infra`。
4. 每个 PR 只包含一个清晰的逻辑改动。
5. 提交 PR 前运行相关测试和检查。

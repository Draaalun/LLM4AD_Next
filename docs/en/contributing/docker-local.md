# Docker Local Startup

This page explains the Docker workflows for contributors. Use it when you are developing the Web UI, debugging the deployment stack, or need the platform services that the Python-only CLI does not require.

## Choose a Mode

| Mode | Command | Use when |
|---|---|---|
| Local infrastructure | `./dev.sh infra` or `.\dev.ps1 infra` | You run the backend and frontend on the host, but want PostgreSQL, Redis, RustFS, mailcatcher, and the code-server proxy in Docker. Recommended for daily development. |
| Full local stack | `./dev.sh full` or `.\dev.ps1 full` | You want Docker to build and run backend, worker, frontend, and infrastructure from the local source tree. Useful for deployment debugging. |
| Image deployment | `./start.sh --debug` | You want to run already-published deployment images, with debug ports exposed. Useful for release verification. |

Run all commands from the `docker/` directory.

## Prerequisites

- Docker Engine with the Compose plugin (`docker compose version`)
- Enough local disk space for PostgreSQL, Redis, RustFS, backend, frontend, and task-runner images
- A writable project home directory for generated user projects

On Linux, the backend mounts `/var/run/docker.sock` so tasks can launch isolated runtime containers. Make sure your user can access Docker.

## Install Docker

This project uses Docker Compose v2 through the `docker compose` command. Verify the installation after setup:

```bash
docker version
docker compose version
```

### Windows: Docker Desktop

Use [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) for local development.

1. Confirm Windows meets Docker Desktop's current system requirements.
2. Enable WSL 2 on Windows if it is not already enabled.
3. Download and run `Docker Desktop Installer.exe`.
4. Use per-user installation unless your organization requires all-users installation.
5. When the installer asks for the backend, select **Use WSL 2 instead of Hyper-V**.
6. Start Docker Desktop from the Start menu and accept the Docker Desktop terms.
7. Open PowerShell and verify:

```powershell
docker version
docker compose version
```

For this project, keep Docker Desktop running while using `.\dev.ps1 ...`. Use Linux containers through WSL 2; Windows containers are not supported by the local compose stack.

Docker Desktop licensing depends on your organization type and size. Check Docker's current subscription terms on the official install page before using it in a company environment.

### macOS: Docker Desktop

Install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/), start Docker Desktop from `/Applications`, accept the Docker Desktop terms, and verify:

```bash
docker version
docker compose version
```

### Linux: Docker Engine

Install [Docker Engine](https://docs.docker.com/engine/install/) for your distribution, then install the [Docker Compose plugin](https://docs.docker.com/compose/install/) if it is not included by your package source.

After installation, make sure your shell can access Docker:

```bash
docker version
docker compose version
```

If `docker version` fails with a permission error, either run Docker commands with `sudo` or follow Docker's post-installation steps for non-root access.

## Create `.env`

Copy the local example and edit required values:

```bash
cd docker
cp .env.develop.local.example .env
```

Windows PowerShell:

```powershell
cd docker
Copy-Item .env.develop.local.example .env
```

Set these values before starting services:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Application secret. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `PROVIDER_ENCRYPTION_KEY` | Stable encryption key for stored provider credentials. Generate it the same way and do not rotate it casually. |
| `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD` | Initial administrator account. |
| `POSTGRES_PASSWORD` | PostgreSQL password. |
| `REDIS_PASSWORD` | Redis password. |
| `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` | RustFS object storage credentials. |
| `HOST_PROJECT_HOME` / `DOCKER_PROJECT_HOME` | Host and container project-home paths. For local debugging they should point to the same absolute path. |

For host-run backend development, keep the service endpoints pointed at localhost:

```dotenv
POSTGRES_SERVER=localhost
REDIS_HOST=localhost
RUSTFS_ENDPOINT=http://localhost:9000
AUTH_BACKEND_URL=http://host.docker.internal:8000
FRONTEND_HOST=http://localhost:5173
CHAT_TUNE_CONTAINER_NETWORK=false
```

## Local Infrastructure Mode

Start only the infrastructure services:

```bash
cd docker
./dev.sh infra
```

Windows PowerShell:

```powershell
cd docker
.\dev.ps1 infra
```

This uses `compose.yml` plus `compose.override.yml`. The override exposes infrastructure ports and disables the application containers so you can run backend and frontend directly on the host.

Exposed services:

| Service | URL / port |
|---|---|
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| RustFS API | `http://localhost:9000` |
| RustFS console | `http://localhost:9001` |
| Adminer | `http://localhost:8080` |
| Mailcatcher UI | `http://localhost:1081` |
| Mailcatcher SMTP | `localhost:1025` |
| Code-server proxy | `http://localhost:8083` |

Then start the backend on the host:

```bash
cd ../src/backend
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Start a worker in another shell when testing async tasks:

```bash
cd ../src/backend
uv run celery -A app.core.celery worker --loglevel=info --concurrency=2
```

Start the frontend:

```bash
cd ../src/frontend
bun install
bun run dev
```

The backend reads `../../docker/.env` by default, so keep running backend commands from `src/backend`.

## Full Local Stack Mode

Build and run the full stack from local source with debug ports:

```bash
cd docker
./dev.sh full
```

Windows PowerShell:

```powershell
cd docker
.\dev.ps1 full
```

This uses `compose.yml` plus `compose.deploy.debug.yml` and enables the `debug` profile. It runs backend, worker, frontend, infrastructure, Adminer, and Flower in Docker.

Useful endpoints:

| Service | URL / port |
|---|---|
| Frontend | `http://localhost:${FRONTEND_PORT}`; default from `.env` is `18041` |
| Backend API | `http://localhost:8000` |
| Adminer | `http://localhost:8080` |
| Flower | `http://localhost:5555` |
| RustFS console | `http://localhost:9001` |

Tail logs:

```bash
./dev.sh logs
./dev.sh logs backend worker
```

Windows PowerShell:

```powershell
.\dev.ps1 logs
.\dev.ps1 logs backend worker
```

Show service status:

```bash
./dev.sh ps
```

Windows PowerShell:

```powershell
.\dev.ps1 ps
```

## Image Deployment Debug Mode

Use `start.sh` when you want deployment images instead of local builds:

```bash
cd docker
TAG=v1.0.0 ./start.sh start --debug
```

`--debug` includes `compose.deploy.debug.yml`, enables the `debug` profile, and exposes PostgreSQL, Redis, RustFS, backend, Adminer, and Flower ports.

## Stop and Clean Up

Stop containers without removing them:

```bash
./dev.sh stop
```

Windows PowerShell:

```powershell
.\dev.ps1 stop
```

Remove compose containers and orphans while keeping bind-mounted data under `docker/app-data/`:

```bash
./dev.sh remove
```

Windows PowerShell:

```powershell
.\dev.ps1 remove
```

For image-based deployments:

```bash
./start.sh stop --debug
./start.sh remove --debug
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Missing docker/.env` | The local env file was not created | Run `cp .env.develop.local.example .env` in `docker/` and edit required values. |
| Compose reports `Variable not set` | Required secrets are still blank | Fill every required value in `.env`. |
| Backend cannot connect to DB or Redis | `.env` still points to Docker service names while backend runs on the host | Use `POSTGRES_SERVER=localhost` and `REDIS_HOST=localhost`. |
| Stored provider credentials disappear after restart | `PROVIDER_ENCRYPTION_KEY` changed or was empty | Set a stable `PROVIDER_ENCRYPTION_KEY` and keep it unchanged for that database. |
| Task containers cannot access generated files | `HOST_PROJECT_HOME` and `DOCKER_PROJECT_HOME` do not match the local path expectation | Use the same absolute path for local debugging and ensure it exists. |
| Ports are already in use | Another service is using the debug port | Change the relevant port in `.env` or stop the conflicting process. |

## Related Docs

- [Development Setup](development.md)
- [Contribution Guidelines](guidelines.md)
- [Web UI Overview](../web-ui/overview.md)

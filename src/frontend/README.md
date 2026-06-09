# LLM4AD_Next - Frontend

## 环境要求

- [Bun](https://bun.sh/) >= 1.0

## 安装 Bun

### macOS / Linux

```bash
curl -fsSL https://bun.sh/install | bash
```

### Windows

```powershell
powershell -c "irm bun.sh/install.ps1 | iex"
```

## 快速开始

1. 安装依赖

```bash
bun install
```

2. 配置环境变量

```bash
cp .env.example .env
```

根据实际情况修改 `.env` 中的值，各字段说明见文件内注释。

3. 启动开发服务器

```bash
bun run dev
```

## 常用命令

| 命令                      | 说明                        |
| ------------------------- | --------------------------- |
| `bun run dev`             | 启动开发服务器              |
| `bun run build`           | 构建生产产物                |
| `bun run generate-client` | 根据 OpenAPI 生成客户端代码 |

## 生成 API 客户端

```bash
# 确认`openapi-ts.config.ts`的`input`配置是否正确
bun run generate-client
```

# MAS - 智能营销助手系统

<div style="text-align: center;">

[![Python](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange.svg)](https://langchain-ai.github.io/langgraph/)

</div>

## 📖 项目简介

MAS（Marketing Agent System）是一个企业级多智能体营销助手平台，专注于数字营销场景的智能化解决方案。系统基于 FastAPI 与 LangGraph 构建，采用"线程 → 工作流 → 智能体"的分层架构，提供完整的会话管理、智能对话、内容生成、情感分析等核心功能。

平台集成了 Redis、Elasticsearch、Milvus 等主流存储方案，支持 Langfuse 全链路可观测性，并提供完整的 Docker Compose 开发与部署环境，可快速集成到现有业务系统中。

## ✨ 核心特性

### 🤖 多智能体工作流
- 基于 LangGraph 的模块化智能体架构
- 内置聊天、合规检查、产品推荐、情感分析、记忆管理等专业模块
- 灵活的工作流编排能力，位于 `api/core/agents` 与 `api/core/graphs`

### 🏗️ 清晰的服务架构
- **Controllers**：RESTful API 路由层
- **Services**：业务逻辑编排层
- **Models/Schemas**：数据模型与验证层
- 遵循领域驱动设计（DDD）最佳实践

### 🔌 灵活的 LLM 集成
- 轻量化多 LLM 运行时系统（`api/infra/runtimes`）
- 默认支持 OpenAI、Anthropic、Gemini
- 通过 `api/data/models.yaml` 轻松扩展更多模型
- 支持自定义模型适配器

### 💾 多层次记忆系统
- **短期存储**：Redis ConversationStore 实现高性能会话缓存
- **长期索引**：Elasticsearch 集成，支持全文检索
- **向量检索**：Milvus 向量数据库，实现语义相似度搜索

### 🔍 完整的可观测性
- 集成 Langfuse 追踪平台
- 完整的调用链路监控
- 实时性能指标与分析

### 🐳 开箱即用的部署方案
- `docker/` 目录提供开发与生产环境 Compose 配置
- 一键启动完整技术栈
- 支持水平扩展与高可用部署

### 🖥️ 现代化前端界面
- `web/` 目录下的 Next.js 运营平台
- 可视化管理面板与数据看板
- 详见子目录文档

## 📂 项目结构

```text
mas/
├── api/                      # FastAPI 后端服务与 LangGraph 智能体工作流
│   ├── controllers/          # API 路由层
│   ├── core/                 # 核心业务能力模块
│   │   ├── agents/           # 智能体实现
│   │   ├── graphs/           # LangGraph 工作流定义
│   │   ├── memory/           # 记忆管理系统
│   │   └── prompts/          # 提示词工程
│   ├── infra/                # 基础设施层
│   │   ├── database/         # 数据库适配
│   │   ├── cache/            # 缓存适配
│   │   └── runtimes/         # LLM 管理器
│   ├── services/             # 业务服务编排层
│   ├── models/               # 数据模型
│   ├── schemas/              # API 请求/响应模型
│   ├── scripts/              # 工具脚本（数据库迁移、初始化等）
│   └── tests/                 # 测试套件（Pytest）
├── docker/                         # Docker 编排配置
│   ├── docker-compose.dev.yml      # 开发环境配置
│   └── docker-compose.yml          # 生产环境配置
├── docs/                           # 项目文档
│   ├── deployment.md               # 部署指南
│   ├── LLM_usage.md          # 多 LLM 配置说明
│   └── database_migrations.md      # 数据库迁移指南
├── web/                  # Next.js 前端应用
└── README.md             # 当前文件
```

## 🚀 快速开始

### 环境要求

- Python 3.13 及以上
- [uv](https://docs.astral.sh/uv/) 包管理器
- Docker Compose
- 至少一组可用的 LLM API Key（OpenAI、Anthropic、Gemini 或 OpenRouter）

### 启动步骤

#### 1. 克隆仓库

```bash
git clone <repo-url>
cd mas
```

#### 2. 启动依赖服务

```bash
# 返回项目根目录
cd docker

docker compose -f docker-compose.dev.yml up -d
```

#### 3. 配置环境变量

复制并编辑环境配置文件：

```bash
cd ../api
cp .env.example .env
```

#### 4. 初始化数据库

```bash
uv run scripts/database.py
```

#### 5. 启动 API 服务

```bash
# 开发模式（热重载）
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或使用快捷方式
uv run main.py
```

#### 6. 验证部署

- **健康检查**：访问 http://localhost:8000/health
- **API 文档**：访问 http://localhost:8000/docs

### 前端部署

前端应用位于 `web/` 目录，详细说明请参见：
- `web/README.md` - 前端项目说明
- `web/REVIEW.md` - 技术架构文档

## 🧪 开发与测试
```bash
# 运行全部测试
cd api
uv run pytest

# 运行特定测试文件
uv run pytest tests/agents/test_agents.py

# 生成覆盖率报告
uv run pytest --cov=. --cov-report=term-missing
```


## 🗄️ 数据库管理

### 数据库迁移

本项目使用 Alembic 进行数据库版本管理，`api/scripts/database.py` 封装了常用操作：

```bash
cd api

# 应用所有未执行的迁移
uv run scripts/database.py

# 创建新的迁移文件（自动检测模型变更）
uv run scripts/database.py revision "add user preferences table"

# 回滚到上一个版本
uv run scripts/database.py downgrade -1

# 回滚到特定版本
uv run scripts/database.py downgrade <revision_id>
```

> 更多详细说明请参见 [`docs/database_migrations.md`](docs/database_migrations.md)


## 📡 API 文档

### 通用接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 服务健康检查，返回系统状态 |
| `/docs` | GET | Swagger UI 交互式 API 文档 |

### 认证模块 (`/v1/auth`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/auth/token` | POST | 通过 `X-App-Key` 颁发服务间 JWT |
| `/v1/auth/verify` | GET | 校验 JWT 并返回解析信息 |
| `/v1/auth/test` | GET | 权限验证示例 |

### 会话线程 (`/v1/threads`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/threads` | POST | 创建新的对话线程 |
| `/v1/threads/{thread_id}` | GET | 查询线程元数据 |
| `/v1/threads/{thread_id}/info` | POST | 更新线程元数据 |
| `/v1/threads/{thread_id}/runs/wait` | POST | 同步运行工作流并等待结果 |
| `/v1/threads/{thread_id}/runs/async` | POST | 异步触发工作流，后台处理 |
| `/v1/threads/{thread_id}/runs/{run_id}/status` | GET | 查询后台运行状态 |

### LLM 直连 (`/v1/messages`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/messages` | POST | 直接发送消息并获取响应 |
| `/v1/messages/responses` | POST | 调用 OpenAI Responses API |
| `/v1/messages/responses/structured` | POST | 结构化输出（基于 Pydantic 模型） |

### 助理管理 (`/v1/assistants`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/assistants` | POST | 创建智能助理 |
| `/v1/assistants/{assistant_id}` | GET | 查看助理详情 |
| `/v1/assistants/{assistant_id}/info` | POST | 更新助理配置 |
| `/v1/assistants/{assistant_id}` | DELETE | 删除助理 |

### 营销专员 (`/v1/marketing`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/marketing/plans` | POST | 营销专家智能对话 |

### 社交媒体工具 (`/v1/social-media`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/social-media/comment` | POST | 生成评论内容 |
| `/v1/social-media/reply` | POST | 生成互动回复 |
| `/v1/social-media/keywords` | POST | 提取主题关键词 |
| `/v1/social-media/chat` | POST | 社媒场景对话 |
| `/v1/social-media/reload-prompt` | POST | 刷新社媒场景 Prompt |

### 租户管理 (`/v1/tenants`)

| 端点 | 方法 | 描述 |
|------|------|------|
| `/v1/tenants/sync` | POST | 从业务系统同步租户信息 |
| `/v1/tenants/{tenant_id}` | GET | 查询租户状态 |
| `/v1/tenants/{tenant_id}` | POST | 更新租户配置 |
| `/v1/tenants/{tenant_id}` | DELETE | 删除租户 |

> 完整的请求/响应参数说明请访问 http://localhost:8000/docs


## 📚 技术文档

| 文档 | 描述 |
|------|------|
| [`docs/README.md`](docs/README.md) | 英文版项目概览 |
| [`docs/deployment.md`](docs/deployment.md) | 部署指南（开发/生产环境） |
| [`docs/database_migrations.md`](docs/database_migrations.md) | 数据库迁移最佳实践 |
| [`docs/LLM_usage.md`](docs/LLM_usage.md) | 多 LLM 运行时配置指南 |

## 🤝 技术支持

- **邮箱**: consumerclone@outlook.com
- **团队**: HuanMu Team

<div style="text-align: center;">

**Made with ❤️ by HuanMu Team**

</div>

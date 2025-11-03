# MAS 智能营销助手

MAS（Marketing Agent System）是面向医美与美妆场景的多智能体营销助手。后端基于 FastAPI 与 LangGraph，围绕“线程 → 工作流 → 智能体”构建会话处理链路，并配套 Redis、Elasticsearch、Milvus 等存储选项以及 Langfuse 观测平台。仓库同时包含 Next.js 前端和完整的 Docker Compose 环境，便于快速体验与调试。

## 功能亮点

- LangGraph 驱动的多智能体工作流，内置聊天、合规、产品、情感、记忆等模块，位于 `api/core/agents` 与 `api/core/workflows`
- FastAPI 服务分层清晰：`controllers` 提供路由，`services` 聚合业务逻辑，`models`/`schemas` 定义数据约束
- 轻量化多 LLM 运行时（`api/infra/runtimes`），默认支持 OpenAI、Anthropic，并可通过 `data/models.yaml` 扩展模型列表
- 会话记忆覆盖 Redis 短期存储（ConversationStore）、可选 Elasticsearch 长期索引与 Milvus 向量检索
- `docker/` 目录提供开发/生产 Compose 文件和 Langfuse 观测链路，适合端到端联调
- `web/` 下的 Next.js 应用用于运营平台与可视化面板（详见子目录自带文档）

## 仓库结构

```text
mas-v0.2/
├── api/                  # FastAPI 后端与 LangGraph 工作流
│   ├── controllers/      # v1 REST 路由（auth、threads、assistants、prompts 等）
│   ├── core/             # 智能体、记忆、工作流、提示词等核心能力
│   ├── infra/            # 数据库、缓存、LLM、观测等基础设施适配
│   ├── services/         # 业务服务层（助理、线程、工作流调度）
│   ├── models/           # Pydantic/SQLAlchemy 模型
│   ├── scripts/          # setup、数据库迁移工具
│   └── test/             # Pytest 测试套件
├── docker/               # 开发与部署用 Compose 定义、Nginx 配置
├── docs/                 # 项目文档（部署、迁移、LLM、存储策略等）
├── web/                  # Next.js 前端与 Langfuse 面板
└── README.md             # 当前文件
```

## 快速开始（后端）

### 环境要求
- Python 3.11 及以上
- [uv](https://docs.astral.sh/uv/) 包管理器（建议 `curl -LsSf https://astral.sh/uv/install.sh | sh`）
- Docker & Docker Compose（可选，用于依赖服务或一体化部署）
- 至少一组可用的 LLM API Key（OpenAI、Anthropic、Gemini 或 OpenRouter）

### 启动步骤
1. 克隆仓库并切换到后端目录：
   ```bash
   git clone <repo-url>
   cd mas-v0.2/api
   ```
2. 运行初始化脚本（安装依赖、生成 `.env` 模板、创建数据目录）：
   ```bash
   ./scripts/setup.sh
   ```
3. 根据实际密钥与服务地址编辑 `.env`。常用变量包括 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`DB_*`、`REDIS_URL`、`ELASTICSEARCH_URL`、`MILVUS_HOST`。
4. 如需本地依赖服务，可在仓库根目录执行：
   ```bash
   docker compose -f docker/docker-compose.dev.yml up -d postgres redis
   # 需要 Langfuse/ClickHouse/MinIO 时再补充相应服务
   ```
5. 启动 API：
   ```bash
   uv run uvicorn main:app --reload
   # 或使用 uv run python main.py
   ```
6. 访问 `http://localhost:8000/` 获取健康信息，`http://localhost:8000/docs` 查看自动生成的 OpenAPI 文档。

前端与 Langfuse 面板位于 `web/` 目录，具体使用方式请参见该目录的 `README.md` 与 `REVIEW.md`。

## 常用命令
```bash
# 运行全部测试
cd api
uv run pytest

# 运行单个测试文件（示例：多智能体集成）
uv run pytest test/agents/test_agents.py

# 生成覆盖率报告
uv run pytest --cov=. --cov-report=term-missing
```

## 数据库迁移
`api/scripts/database.py` 封装了 Alembic 常用流程：

```bash
cd api

# 应用最新迁移
uv run python scripts/database.py

# 创建新迁移（自动检测模型变更）
uv run python scripts/database.py revision "add tenant webhook"

# 回滚到上一版本
uv run python scripts/database.py downgrade -1
```

现有迁移位于 `api/migrations/versions/6ee06edc35dd_modify_data_model.py`，更多注意事项请参见 `docs/database_migrations.md`。

## API 概览

### 通用
- `GET /`：服务健康信息

### 认证 (`/v1/auth`)
- `POST /v1/auth/token`：通过 `X-App-Key` 颁发服务间 JWT
- `GET /v1/auth/verify`：校验 JWT 并返回解析信息
- `GET /v1/auth/test`：校验 `backend:admin` 权限示例

### 会话线程 (`/v1/threads`)
- `POST /v1/threads`：创建对话线程（需要租户上下文）
- `GET /v1/threads/{thread_id}`：查询线程元数据
- `POST /v1/threads/{thread_id}/runs/wait`：同步运行 LangGraph 工作流
- `POST /v1/threads/{thread_id}/runs/async`：异步触发工作流，后台处理
- `GET /v1/threads/{thread_id}/runs/{run_id}/status`：查询后台运行状态

### LLM 直连 (`/v1/messages`)
- `POST /v1/messages`：直接发送消息并获取 `LLMClient` 响应
- `POST /v1/messages/responses`：调用 OpenAI Responses API
- `POST /v1/messages/responses/structured`：基于 Pydantic 模型的结构化输出

### 助理管理 (`/v1/assistants`)
- `POST /v1/assistants`：创建智能助理
- `GET /v1/assistants/{assistant_id}`：查看助理详情
- `PUT /v1/assistants/{assistant_id}`：更新助理配置
- `DELETE /v1/assistants/{assistant_id}`：删除助理（需提供租户 ID）

### Prompt 管理 (`/v1/prompts`)
- `POST /v1/prompts/{assistant_id}`：创建或替换助理 Prompt
- `GET /v1/prompts/{assistant_id}/{tenant_id}/{version}`：读取指定版本
- `PUT /v1/prompts/{tenant_id}/{assistant_id}`：更新 Prompt 版本
- `POST /v1/prompts/{assistant_id}/rollback`：回滚到历史版本
- 另含模板库、克隆、校验等辅助端点

### 社交渠道工具 (`/v1/social-media`)
- `POST /v1/social-media/comment`：生成评论内容
- `POST /v1/social-media/reply`：生成互动回复
- `POST /v1/social-media/keywords`：提取主题关键词
- `POST /v1/social-media/chat`：社媒场景对话
- `POST /v1/social-media/reload-prompt`：刷新社媒场景 Prompt

### 租户同步 (`/v1/tenants`)
- `POST /v1/tenants/sync`：从业务系统同步租户信息
- `GET /v1/tenants/{tenant_id}/status`：查询租户状态
- `PUT /v1/tenants/{tenant_id}`：更新租户特性或状态
- `DELETE /v1/tenants/{tenant_id}`：删除租户

完整参数说明与响应模型可通过 FastAPI 文档或 `schemas/` 目录查看。

## 更多文档
- `docs/README.md`：英文概览与快速开始
- `docs/DEPLOYMENT.md`：开发/生产部署指引
- `docs/database_migrations.md`：Alembic 使用与团队协作
- `docs/MULTI_LLM_USAGE.md`：多 LLM 运行时配置与调用示例
- `docs/message-storage-strategy.md`：会话与记忆存储策略

## 技术支持
- 邮箱：consumerclone@outlook.com
- 团队：HuanMu Team
```

#!/bin/bash

# MAS 开发环境配置脚本
# 用于自动化设置多智能体营销系统的开发环境

set -e

echo "🚀 正在设置 MAS 营销智能体开发环境..."

# 检查 uv 是否已安装
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装。请先安装 uv："
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ 找到 uv: $(uv --version)"

# Install dependencies
echo "📦 正在安装项目依赖..."
uv sync

# 如果 .env 文件不存在则创建
if [ ! -f .env ]; then
    echo "📝 正在创建.env环境配置文件..."
    
    # 优先使用 .env.example 模板
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ 从 .env.example 创建 .env 文件"
    else
        # 创建默认的环境配置文件
        cat > .env << EOL
# === LLM 提供商 API 密钥 ===
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# === 数据库配置 ===
# PostgreSQL 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mas_tenants
POSTGRES_USER=mas_user
POSTGRES_PASSWORD=mas_pass

# === Memory & RAG Configuration ===
# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200

# Redis
REDIS_URL=redis://localhost:6379

# Milvus 向量数据库
MILVUS_HOST=localhost
MILVUS_PORT=19530

# === APP配置 ===
APP_HOST=0.0.0.0
APP_PORT=8000
APP_ENV=development
DEBUG=true

# 默认和备用 LLM 提供商
DEFAULT_LLM_PROVIDER=openai
FALLBACK_LLM_PROVIDER=anthropic

# 启用成本追踪和智能路由
ENABLE_COST_TRACKING=true
ENABLE_INTELLIGENT_ROUTING=true

# === Service Authentication ===
APP_KEY=your_backend_app_key_here
APP_JWT_ISSUER=mas-ai-service
APP_JWT_AUDIENCE=ai-admin
APP_TOKEN_TTL=300

# === Logging ===
LOG_LEVEL=INFO
LOG_FILE=logs/mas.log

# === 性能配置 ===
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30
CACHE_TTL=3600
EOL
        echo "✅ 创建默认 .env 文件"
    fi
    echo "⚠️  请更新 .env 文件中的 API 密钥和数据库凭据"
fi

# 创建必要的目录
echo "📁 正在创建必需目录..."
mkdir -p logs data/uploads data/vector_store data/cache

# 检查 Docker 是否可用
if command -v docker &> /dev/null; then
    echo "✅ 找到 Docker: $(docker --version | head -1)"
else
    echo "⚠️  未找到 Docker。运行基础设施服务需要 Docker。"
fi

echo "✅ 开发环境设置完成！"
echo ""
echo "下一步操作："
echo "1. 🔑 更新 .env 文件中的 API 密钥 (OpenAI, Anthropic, Google, DeepSeek)"
echo "2. 🗄️ 更新 .env 文件中的数据库凭据"
echo "3. 🐳 启动基础设施服务: ./scripts/docker-dev.sh up"
echo "4. 🧪 运行测试: uv run pytest"
echo "5. 🚀 启动开发服务器: uv run main.py"
echo ""
echo "📚 更多信息请参见 README.md"
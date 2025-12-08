"""
API Package - Multi-Agent System API

该包包含完整的FastAPI应用程序和所有API组件：

组织结构:
- workspace/: 工作空间组件
- inner/: 内部组件
- middleware/: 中间件组件
- exceptions.py: 异常处理
- dependencies.py: 依赖注入

核心功能:
- 智能体管理和测试
- 对话处理和历史管理
- 多LLM提供商管理
- 多模态内容处理
- 系统健康监控
- 多租户数据隔离
"""

from fastapi import APIRouter

from .console import tenant_router, auth_router, health_router
from .inner import completion_router
from .workspace import (
    conversations_router,
    assistants_router,
    prompts_router,
    public_traffic_router,
    text_beautify_router,
)


app_router = APIRouter()

# 注册所有路由器，包含统一的prefix和tags配置
app_router.include_router(auth_router, prefix="/auth", tags=["auth"])
app_router.include_router(conversations_router, prefix="/threads", tags=["conversation-threads"])
app_router.include_router(assistants_router, prefix="/assistants", tags=["assistants"])
app_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
app_router.include_router(public_traffic_router, prefix="/social-media", tags=["social-media"])
app_router.include_router(text_beautify_router, prefix="/social-media", tags=["social-media"])
app_router.include_router(tenant_router, prefix="/tenants", tags=["tenant"])
app_router.include_router(completion_router, prefix="/messages", tags=["messages"])
app_router.include_router(health_router, tags=["health"])


__version__ = "0.2.1"

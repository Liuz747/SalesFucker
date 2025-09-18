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

from .console import tenant_router, auth_router
from .inner import completion_router, health_router
from .workspace import conversations_router

app = APIRouter()

__version__ = "0.2.1"

__all__ = [
    "health_router",
    "conversations_router",
    "tenant_router",
    "completion_router",
    "auth_router"
]
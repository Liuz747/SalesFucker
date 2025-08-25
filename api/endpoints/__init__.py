"""
API端点模块

该模块包含所有API端点的路由定义。

端点组织:
- agents.py: 智能体管理和测试端点
- conversations.py: 对话处理端点
- multimodal.py: 多模态处理端点
- health.py: 健康检查端点
"""

from .agents import router as agents_router
from .conversations import router as conversations_router
from .multimodal import router as multimodal_router
from .health import router as health_router
from .assistants import router as assistants_router
from .prompts import router as prompts_router
from .service_auth import router as auth_router
from .tenant import router as tenant_router

__all__ = [
    "agents_router",
    "auth_router",
    "conversations_router", 
    "multimodal_router",
    "health_router",
    "assistants_router",
    "prompts_router",
    "tenant_router"
]
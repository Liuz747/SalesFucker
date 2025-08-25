"""
API Package - Multi-Agent System API

该包包含完整的FastAPI应用程序和所有API组件：

组织结构:
- endpoints/: API路由处理器
- handlers/: 业务逻辑处理器  
- schemas/: Pydantic数据模型
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

from .endpoints import (
    agents_router,
    conversations_router,
    multimodal_router,
    health_router
)

__version__ = "1.0.0"

__all__ = [
    "agents_router",
    "conversations_router", 
    "multimodal_router",
    "health_router"
]
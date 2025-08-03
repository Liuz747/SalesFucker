"""
API Route Handlers

This package contains API route handlers and endpoints:
- Conversation endpoints
- Multi-modal input handlers
- Multi-LLM provider management
- Tenant routing
- Agent-specific endpoints
"""

from fastapi import APIRouter
from .agents import router as agents_router
from .agent_endpoints import router as agent_test_router
from .multi_llm_endpoints import router as multi_llm_router
from .multi_llm_admin_endpoints import router as multi_llm_admin_router
from .v1.multimodal import router as multimodal_router

# 创建主路由器
api_router = APIRouter(prefix="/api", tags=["api"])

# 注册子路由器
api_router.include_router(agents_router)
api_router.include_router(agent_test_router)
api_router.include_router(multi_llm_router)
api_router.include_router(multi_llm_admin_router)
api_router.include_router(multimodal_router)

__all__ = [
    "api_router", 
    "agents_router", 
    "agent_test_router",
    "multi_llm_router",
    "multi_llm_admin_router",
    "multimodal_router"
] 
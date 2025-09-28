"""
API端点模块

该模块包含所有API端点的路由定义。

端点组织:
- agents.py: 智能体管理和测试端点
- multimodal.py: 多模态处理端点
"""

from .multimodal import router as multimodal_router
from controllers.workspace.assistants.assistants_controller import router as assistants_router
from controllers.workspace.prompts.prompts_controller import router as prompts_router

__all__ = [
    "multimodal_router",
    "assistants_router",
    "prompts_router"
]
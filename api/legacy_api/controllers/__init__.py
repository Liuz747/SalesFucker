"""
API端点模块

该模块包含所有API端点的路由定义。

端点组织:
- agents.py: 智能体管理和测试端点
- multimodal.py: 多模态处理端点
"""

from .multimodal import router as multimodal_router

__all__ = [
    "multimodal_router",
]
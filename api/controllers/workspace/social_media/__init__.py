"""
社交媒体模块路由

包含社交媒体相关的所有API路由组件。
"""

from .public_traffic import router as public_traffic_router
from .text_beautify import router as text_beautify_router

__all__ = [
    "public_traffic_router",
    "text_beautify_router",
]
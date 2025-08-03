"""
多模态API端点（重构版）

该模块提供多模态交互的FastAPI端点。
支持语音上传、图像上传和多模态对话处理。
重构后采用模块化设计，提高代码组织性和可维护性。

核心功能:
- 语音文件上传和处理
- 图像文件上传和分析
- 多模态对话管理
- 实时处理状态追踪

注意: 完整的端点实现已移至 multimodal_endpoints.py
"""

from fastapi import APIRouter
from src.api.v1.multimodal_endpoints import router as endpoints_router

# 创建主路由器
router = APIRouter(prefix="/multimodal", tags=["multimodal"])

# 包含所有端点
router.include_router(endpoints_router, prefix="")

# 向后兼容性 - 重新导出关键组件
from src.api.v1.multimodal_handlers import MultiModalAPIHandler
from src.api.v1.multimodal_tasks import MultiModalTaskProcessor
from src.api.v1.multimodal_utils import (
    create_audio_attachment,
    create_image_attachment,
    build_upload_response,
    build_multimodal_response,
    build_status_response,
    build_health_response
)

# 全局处理器实例（向后兼容）
api_handler = MultiModalAPIHandler()
task_processor = MultiModalTaskProcessor(api_handler)

__all__ = [
    'router',
    'api_handler', 
    'task_processor',
    'MultiModalAPIHandler',
    'MultiModalTaskProcessor',
    'create_audio_attachment',
    'create_image_attachment',
    'build_upload_response',
    'build_multimodal_response',
    'build_status_response',
    'build_health_response'
]
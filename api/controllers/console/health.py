"""
健康检查端点

GET /health - 基础健康检查
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import mas_config
from utils import get_component_logger, to_isoformat

logger = get_component_logger(__name__, "HealthCheck")

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    基础健康检查

    返回服务基本状态信息，确认服务正在运行
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": mas_config.APP_NAME,
            "timestamp": to_isoformat()
        }
    )
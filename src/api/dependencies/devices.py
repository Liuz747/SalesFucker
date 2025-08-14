"""
设备相关依赖
"""

from fastapi import HTTPException, Depends

from src.auth.jwt_auth import get_service_context
from src.auth.models import ServiceContext
from src.external.clients.device_client import DeviceClient
from src.external.config import get_external_config


async def get_device_client() -> DeviceClient:
    """返回设备客户端"""
    try:
        config = get_external_config()
        return DeviceClient(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "DEVICE_CLIENT_UNAVAILABLE", "message": "设备查询服务暂时不可用"})


async def validate_device_access(
    device_id: str,
    service: ServiceContext = Depends(get_service_context),
    device_client: DeviceClient = Depends(get_device_client),
) -> str:
    """校验设备归属与存在性"""
    # In trust model, backend service manages all device access
    # Device access validation will be implemented in future versions

    try:
        # Note: Will need tenant_id from request context
        info = await device_client.get_device(device_id, "default_tenant")
        if not info:
            raise HTTPException(status_code=404, detail={"error": "DEVICE_NOT_FOUND", "message": f"设备 {device_id} 不存在"})
        return device_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "DEVICE_VALIDATION_FAILED", "message": "设备验证失败，请稍后重试"})



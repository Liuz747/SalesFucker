"""
设备相关依赖
"""

from fastapi import HTTPException, Depends

from src.auth import get_jwt_tenant_context, JWTTenantContext
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
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context),
    device_client: DeviceClient = Depends(get_device_client),
) -> str:
    """校验设备归属与存在性"""
    if not tenant_context.can_access_device(device_id):
        raise HTTPException(status_code=403, detail={"error": "DEVICE_ACCESS_DENIED", "message": f"租户无权访问设备 {device_id}"})

    try:
        info = await device_client.get_device(device_id, tenant_context.tenant_id)
        if not info:
            raise HTTPException(status_code=404, detail={"error": "DEVICE_NOT_FOUND", "message": f"设备 {device_id} 不存在或不属于租户 {tenant_context.tenant_id}"})
        return device_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "DEVICE_VALIDATION_FAILED", "message": "设备验证失败，请稍后重试"})



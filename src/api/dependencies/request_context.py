"""
请求上下文依赖
"""

from typing import Dict, Any
from fastapi import Request, Depends

from src.auth.jwt_auth import get_service_context
from src.auth.models import ServiceContext


async def get_request_context(
    request: Request,
    service: ServiceContext = Depends(get_service_context)
) -> Dict[str, Any]:
    """返回请求上下文（租户、IP、UA、请求ID等）"""
    return {
        "tenant_id": "system",  # Service context, not tenant-specific
        "service_context": service,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": request.headers.get("x-request-id", "unknown"),
        "method": request.method,
        "url": str(request.url),
    }



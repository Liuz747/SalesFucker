"""
请求上下文依赖
"""

from typing import Dict, Any
from fastapi import Request, Depends

from infra.auth.jwt_auth import get_service_context
from infra.auth.jwt_auth import ServiceContext


async def get_request_context(
    request: Request,
    service: ServiceContext = Depends(get_service_context)
) -> Dict[str, Any]:
    """返回请求上下文（租户、IP、UA、请求ID等）"""
    return {
        "tenant_id": request.tenant_id if request.tenant_id else request.metadata.tenant_id,  # Service context, not tenant-specific
        "service_context": service,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": request.headers.get("x-request-id", "unknown"),
        "method": request.method,
        "url": str(request.url),
    }



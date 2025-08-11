"""
请求上下文依赖
"""

from typing import Dict, Any
from fastapi import Request, Depends

from src.auth import get_jwt_tenant_context, JWTTenantContext


async def get_request_context(
    request: Request,
    tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
) -> Dict[str, Any]:
    """返回请求上下文（租户、IP、UA、请求ID等）"""
    return {
        "tenant_id": tenant_context.tenant_id,
        "tenant_context": tenant_context,
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": request.headers.get("x-request-id", "unknown"),
        "method": request.method,
        "url": str(request.url),
    }



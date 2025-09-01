"""
请求上下文依赖
"""

from typing import Dict, Any
from fastapi import Request


async def get_request_context(request: Request) -> Dict[str, Any]:
    """返回请求上下文（租户、UA等）"""
    return {
        "tenant_id": request.state.tenant_id,
    }



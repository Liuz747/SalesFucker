"""
服务间认证（App-Key）

POST /v1/auth/token
    Header: X-App-Key: <app_key>
    Body (optional): { "scopes": ["backend:admin"] }
返回：短期HS256 JWT（仅用于后端→AI的管理调用）
"""

from datetime import timedelta
from typing import List, Optional, Dict, Any

import jwt
from fastapi import APIRouter, Header, HTTPException, status, Depends

from config.settings import settings
from src.utils import get_current_datetime, format_timestamp
from src.auth.jwt_auth import get_service_context, require_service_scopes
from src.auth.models import ServiceContext


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
async def issue_service_token(
    x_app_key: str = Header(..., alias="X-App-Key"),
    payload: Optional[Dict[str, Any]] = None,
):
    # 配置检查
    if not settings.app_key or not settings.app_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "APP_AUTH_NOT_CONFIGURED",
                "message": "App-Key 或 JWT 密钥未配置",
            },
        )

    # App-Key 校验
    if x_app_key != settings.app_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_APP_KEY", "message": "无效或缺失 App-Key"},
        )

    # 生成短期服务令牌
    now = get_current_datetime()
    exp = now + timedelta(seconds=settings.app_token_ttl_seconds)
    body_scopes: List[str] = []
    if payload and isinstance(payload, dict):
        body_scopes = list(payload.get("scopes", []))

    claims = {
        "iss": settings.app_jwt_issuer,
        "aud": settings.app_jwt_audience,
        "sub": "backend-service",
        "scope": body_scopes or ["backend:admin"],
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": f"svc_{int(now.timestamp())}",
    }

    token = jwt.encode(claims, settings.app_jwt_secret, algorithm="HS256")

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.app_token_ttl_seconds,
        "issued_at": format_timestamp(now),
        "scopes": claims["scope"],
    }


@router.get("/verify")
async def verify_service_token(
    service_context: ServiceContext = Depends(get_service_context)
):
    """
    验证服务JWT token
    
    测试端点，用于验证服务JWT认证是否正常工作。
    需要在请求头中包含有效的服务JWT token。
    """
    return {
        "status": "success",
        "message": "服务JWT token验证成功",
        "service_info": {
            "sub": service_context.sub,
            "iss": service_context.iss,
            "scopes": service_context.scopes,
            "verification_time": service_context.verification_timestamp.isoformat(),
            "token_source": service_context.token_source
        }
    }


@router.get("/test")
async def test_admin_access(service: ServiceContext = Depends(require_service_scopes("backend:admin"))):
    """
    测试管理员权限端点
    
    演示如何使用服务管理员权限验证。
    只有具有 backend:admin 权限的服务JWT才能访问。
    """
    return {
        "status": "success", 
        "message": "管理员权限验证成功",
        "admin_info": {
            "service": service.sub,
            "scopes": service.scopes,
            "is_admin": service.is_admin()
        }
    }



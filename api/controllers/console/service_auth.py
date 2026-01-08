"""
服务间认证（App-Key）

POST /v1/auth/token
    Header: X-App-Key: <app_key>
    Body (optional): { "scopes": ["backend:admin"] }
返回：JWT token (MAS内部管理密钥对)
"""

from datetime import timedelta
from typing import Optional, Any

import jwt
from fastapi import APIRouter, Header, HTTPException, status, Depends

from config import mas_config
from utils import get_current_datetime, to_isoformat
from infra.auth import get_service_context, require_service_scopes, ServiceContext, key_manager


router = APIRouter()


@router.post("/token")
async def issue_service_token(
    x_app_key: str = Header(..., alias="X-App-Key"),
    payload: Optional[dict[str, Any]] = None,
):
    # 配置检查
    if not mas_config.APP_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "APP_AUTH_NOT_CONFIGURED",
                "message": "App-Key 未配置",
            },
        )

    # App-Key 校验
    if x_app_key != mas_config.APP_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "INVALID_APP_KEY", "message": "无效或缺失 App-Key"},
        )

    # 检查是否需要生成新密钥对
    if not key_manager.is_key_valid(x_app_key):
        # 生成新的RSA密钥对
        key_manager.generate_key_pair(x_app_key, 30)

    # 生成JWT声明
    now = get_current_datetime()
    exp = now + timedelta(seconds=mas_config.APP_TOKEN_TTL)
    body_scopes: list[str] = []
    if payload and isinstance(payload, dict):
        body_scopes = list(payload.get("scopes", []))

    claims = {
        "iss": mas_config.APP_JWT_ISSUER,
        "aud": mas_config.APP_JWT_AUDIENCE,
        "sub": "backend-service",
        "scope": body_scopes or ["backend:admin"],
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": f"svc_{int(now.timestamp())}",
    }

    # 获取私钥用于签名JWT  
    import json
    key_file = key_manager._get_key_file_path(x_app_key)
    with open(key_file, 'r') as f:
        key_data = json.load(f)
        private_key = key_data["private_key"]

    token = jwt.encode(claims, private_key, algorithm="RS256")

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": mas_config.APP_TOKEN_TTL,
        "issued_at": to_isoformat(now),
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

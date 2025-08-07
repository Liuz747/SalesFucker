"""
JWT认证核心模块

该模块提供JWT token的验证、解析和租户上下文提取功能，
实现基于RSA-256签名的安全认证机制。

核心功能:
- JWT token验证和解析
- 租户身份提取和权限检查
- 安全异常处理和审计日志
- FastAPI依赖注入集成
"""

import jwt
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, Depends
from cryptography.hazmat.primitives import serialization

from .models import JWTTenantContext, JWTVerificationResult, TenantRole
from .tenant_manager import get_tenant_manager, TenantManager
from src.utils import get_component_logger

logger = get_component_logger(__name__, "JWTAuth")


class JWTVerificationError(Exception):
    """JWT验证异常"""
    
    def __init__(self, error_code: str, message: str, details: Optional[Dict] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class TenantAccessError(Exception):
    """租户访问异常"""
    
    def __init__(self, tenant_id: str, message: str, details: Optional[Dict] = None):
        self.tenant_id = tenant_id
        self.message = message  
        self.details = details or {}
        super().__init__(message)


async def verify_jwt_token(
    token: str,
    tenant_manager: TenantManager
) -> JWTVerificationResult:
    """
    验证JWT token并提取租户上下文
    
    参数:
        token: JWT token字符串
        tenant_manager: 租户管理器实例
        
    返回:
        JWTVerificationResult: 验证结果
    """
    try:
        # 解析token header获取租户信息
        unverified_header = jwt.get_unverified_header(token)
        
        # 从token payload中提取租户ID（无验证解析）
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        tenant_id = unverified_payload.get("tenant_id")
        
        if not tenant_id:
            return JWTVerificationResult(
                is_valid=False,
                error_code="MISSING_TENANT_ID",
                error_message="JWT token中缺少租户ID",
                verification_details={"header": unverified_header}
            )
        
        # 获取租户配置
        tenant_config = await tenant_manager.get_tenant_config(tenant_id)
        if not tenant_config:
            return JWTVerificationResult(
                is_valid=False,
                error_code="UNKNOWN_TENANT",
                error_message=f"未知的租户ID: {tenant_id}",
                verification_details={"tenant_id": tenant_id}
            )
        
        if not tenant_config.is_active:
            return JWTVerificationResult(
                is_valid=False,
                error_code="TENANT_DISABLED",
                error_message=f"租户已被禁用: {tenant_id}",
                verification_details={"tenant_id": tenant_id}
            )
        
        # 加载RSA公钥
        try:
            public_key = serialization.load_pem_public_key(
                tenant_config.jwt_public_key.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"加载租户公钥失败: {tenant_id}, 错误: {e}")
            return JWTVerificationResult(
                is_valid=False,
                error_code="INVALID_PUBLIC_KEY", 
                error_message="租户公钥格式无效",
                verification_details={"tenant_id": tenant_id}
            )
        
        # 验证JWT签名和声明
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[tenant_config.jwt_algorithm],
                issuer=tenant_config.jwt_issuer,
                audience=tenant_config.jwt_audience,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "jti"],
                    "verify_exp": True,
                    "verify_iat": True,
                }
            )
        except jwt.ExpiredSignatureError:
            return JWTVerificationResult(
                is_valid=False,
                error_code="TOKEN_EXPIRED",
                error_message="JWT token已过期",
                verification_details={"tenant_id": tenant_id}
            )
        except jwt.InvalidTokenError as e:
            return JWTVerificationResult(
                is_valid=False,
                error_code="INVALID_TOKEN",
                error_message=f"JWT token验证失败: {str(e)}",
                verification_details={
                    "tenant_id": tenant_id,
                    "jwt_error": str(e)
                }
            )
        
        # 验证时间约束
        current_time = datetime.now(timezone.utc)
        issued_at = datetime.fromtimestamp(payload.get("iat"), timezone.utc)
        max_age = tenant_config.max_token_age_minutes * 60
        
        if (current_time - issued_at).total_seconds() > max_age:
            return JWTVerificationResult(
                is_valid=False,
                error_code="TOKEN_TOO_OLD",
                error_message=f"Token签发时间过早，超过最大允许延迟",
                verification_details={
                    "tenant_id": tenant_id,
                    "issued_at": issued_at.isoformat(),
                    "max_age_seconds": max_age
                }
            )
        
        # 构建租户上下文
        tenant_context = JWTTenantContext(
            tenant_id=tenant_id,
            sub=payload.get("sub"),
            iss=payload.get("iss"),
            aud=payload.get("aud"),
            exp=datetime.fromtimestamp(payload.get("exp"), timezone.utc),
            iat=issued_at,
            jti=payload.get("jti"),
            roles=[TenantRole(role) for role in payload.get("roles", [])],
            permissions=payload.get("permissions", []),
            allowed_agents=payload.get("allowed_agents"),
            allowed_devices=payload.get("allowed_devices"),
            rate_limit_per_minute=payload.get(
                "rate_limit_per_minute", 
                tenant_config.rate_limit_config.get("per_minute", 100)
            ),
            daily_quota=payload.get(
                "daily_quota", 
                tenant_config.rate_limit_config.get("per_day", 10000)
            ),
            tenant_name=payload.get("tenant_name", tenant_config.tenant_name),
            tenant_type=payload.get("tenant_type"),
            token_source="Authorization Header",
            verification_timestamp=current_time
        )
        
        # 记录成功访问
        await tenant_manager.record_access(tenant_id, current_time)
        
        return JWTVerificationResult(
            is_valid=True,
            tenant_context=tenant_context,
            verification_details={
                "tenant_id": tenant_id,
                "verification_time": current_time.isoformat(),
                "token_age_seconds": (current_time - issued_at).total_seconds()
            }
        )
        
    except Exception as e:
        logger.error(f"JWT验证过程异常: {e}", exc_info=True)
        return JWTVerificationResult(
            is_valid=False,
            error_code="VERIFICATION_ERROR",
            error_message=f"JWT验证过程发生异常: {str(e)}",
            verification_details={"exception": str(e)}
        )


async def get_jwt_tenant_context(
    authorization: Optional[str] = Header(None),
    tenant_manager: TenantManager = Depends(get_tenant_manager)
) -> JWTTenantContext:
    """
    FastAPI依赖：从JWT token中提取租户上下文
    
    参数:
        authorization: Authorization header值
        tenant_manager: 租户管理器（依赖注入）
        
    返回:
        JWTTenantContext: 验证成功的租户上下文
        
    异常:
        HTTPException: 认证失败时抛出401或403错误
    """
    # 检查Authorization header
    if not authorization:
        logger.warning("缺少Authorization header")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_AUTHORIZATION",
                "message": "缺少Authorization header"
            }
        )
    
    # 解析Bearer token
    auth_parts = authorization.split()
    if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
        logger.warning(f"无效的Authorization格式: {authorization[:50]}...")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_AUTHORIZATION_FORMAT",
                "message": "Authorization header格式必须为: Bearer <token>"
            }
        )
    
    token = auth_parts[1]
    
    # 基本token格式检查
    if len(token) < 50:  # JWT tokens通常很长
        logger.warning("Token长度异常")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_TOKEN_FORMAT",
                "message": "Token格式无效"
            }
        )
    
    # 验证JWT token
    try:
        verification_result = await verify_jwt_token(token, tenant_manager)
        
        if not verification_result.is_valid:
            logger.warning(
                f"JWT验证失败: {verification_result.error_code} - "
                f"{verification_result.error_message}"
            )
            
            # 根据错误类型返回适当的HTTP状态码
            status_code = 401
            if verification_result.error_code in ["TENANT_DISABLED", "ACCESS_DENIED"]:
                status_code = 403
            
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": verification_result.error_code,
                    "message": verification_result.error_message
                }
            )
        
        return verification_result.tenant_context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT认证异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "AUTHENTICATION_ERROR",
                "message": "认证服务暂时不可用"
            }
        )


async def validate_tenant_access(
    tenant_context: JWTTenantContext,
    required_permissions: Optional[list] = None,
    required_roles: Optional[list] = None
) -> None:
    """
    验证租户访问权限
    
    参数:
        tenant_context: 租户上下文
        required_permissions: 必需的权限列表
        required_roles: 必需的角色列表
        
    异常:
        HTTPException: 权限不足时抛出403错误
    """
    # 检查必需权限
    if required_permissions:
        missing_permissions = [
            perm for perm in required_permissions
            if not tenant_context.has_permission(perm)
        ]
        
        if missing_permissions:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "INSUFFICIENT_PERMISSIONS",
                    "message": f"缺少必需权限: {', '.join(missing_permissions)}",
                    "required_permissions": required_permissions,
                    "current_permissions": tenant_context.permissions
                }
            )
    
    # 检查必需角色
    if required_roles:
        has_required_role = any(
            tenant_context.has_role(TenantRole(role))
            for role in required_roles
        )
        
        if not has_required_role:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "INSUFFICIENT_ROLES", 
                    "message": f"需要以下角色之一: {', '.join(required_roles)}",
                    "required_roles": required_roles,
                    "current_roles": [role.value for role in tenant_context.roles]
                }
            )


def require_permissions(*permissions: str):
    """权限依赖装饰器"""
    async def permission_dependency(
        tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
    ) -> JWTTenantContext:
        await validate_tenant_access(
            tenant_context, 
            required_permissions=list(permissions)
        )
        return tenant_context
    
    return permission_dependency


def require_roles(*roles: str):
    """角色依赖装饰器"""
    async def role_dependency(
        tenant_context: JWTTenantContext = Depends(get_jwt_tenant_context)
    ) -> JWTTenantContext:
        await validate_tenant_access(
            tenant_context,
            required_roles=list(roles)
        )
        return tenant_context
    
    return role_dependency
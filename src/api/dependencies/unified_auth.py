"""
统一认证依赖模块

提供支持多种认证方式的FastAPI依赖函数：
1. 用户JWT认证（租户基础认证）
2. 服务JWT认证（后端服务认证）

根据JWT token的特征自动识别认证类型并进行相应验证。
"""

from fastapi import HTTPException, Header, Depends
from typing import Optional
from src.auth.jwt_auth import get_jwt_tenant_context, get_service_context
from src.auth.models import JWTTenantContext, ServiceContext
from src.utils import get_component_logger
import jwt

logger = get_component_logger(__name__, "UnifiedAuth")


class AuthContext:
    """统一认证上下文"""
    
    def __init__(self, tenant_context: Optional[JWTTenantContext] = None, 
                 service_context: Optional[ServiceContext] = None):
        self.tenant_context = tenant_context
        self.service_context = service_context
        self.is_service_auth = service_context is not None
        self.is_tenant_auth = tenant_context is not None
    
    @property
    def tenant_id(self) -> Optional[str]:
        """获取租户ID"""
        if self.tenant_context:
            return self.tenant_context.tenant_id
        return None
    
    def can_access_tenant(self, tenant_id: str) -> bool:
        """检查是否可以访问指定租户"""
        if self.service_context:
            # 服务认证具有跨租户访问权限
            return self.service_context.has_scope("backend:admin")
        elif self.tenant_context:
            # 租户认证只能访问自己的租户
            return self.tenant_context.tenant_id == tenant_id
        return False
    
    def can_access_device(self, device_id: str) -> bool:
        """检查是否可以访问指定设备"""
        if self.service_context:
            # 服务认证具有设备访问权限
            return self.service_context.has_scope("backend:admin")
        elif self.tenant_context:
            return self.tenant_context.can_access_device(device_id)
        return False


async def _detect_auth_type(authorization: Optional[str]) -> str:
    """
    检测JWT认证类型
    
    通过分析JWT payload来判断是用户认证还是服务认证
    """
    if not authorization:
        return "none"
    
    # 解析Bearer token
    auth_parts = authorization.split()
    if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
        return "invalid"
    
    token = auth_parts[1]
    
    try:
        # 无验证解析获取payload
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        
        # 根据subject字段判断认证类型
        sub = unverified_payload.get("sub")
        if sub == "backend-service":
            return "service"
        elif "tenant_id" in unverified_payload:
            return "tenant"
        else:
            # 如果有scope字段且没有tenant_id，也可能是服务认证
            if "scope" in unverified_payload and "tenant_id" not in unverified_payload:
                return "service"
            return "tenant"  # 默认尝试租户认证
            
    except Exception as e:
        logger.warning(f"JWT认证类型检测失败: {e}")
        return "invalid"


async def get_unified_auth_context(
    authorization: Optional[str] = Header(None)
) -> AuthContext:
    """
    统一认证依赖函数
    
    自动检测JWT类型并进行相应的认证验证：
    - 服务JWT: 使用HS256验证，获取ServiceContext
    - 用户JWT: 使用RS256验证，获取JWTTenantContext
    
    参数:
        authorization: Authorization header值
        
    返回:
        AuthContext: 统一认证上下文
        
    异常:
        HTTPException: 认证失败时抛出401或403错误
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_AUTHORIZATION",
                "message": "缺少Authorization header"
            }
        )
    
    # 检测认证类型
    auth_type = await _detect_auth_type(authorization)
    
    if auth_type == "invalid":
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_AUTHORIZATION_FORMAT",
                "message": "Authorization header格式无效"
            }
        )
    elif auth_type == "none":
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_AUTHORIZATION",
                "message": "缺少有效的认证信息"
            }
        )
    
    try:
        if auth_type == "service":
            # 使用服务认证
            service_context = await get_service_context(authorization)
            return AuthContext(service_context=service_context)
        else:
            # 使用租户认证
            tenant_context = await get_jwt_tenant_context(authorization)
            return AuthContext(tenant_context=tenant_context)
            
    except HTTPException:
        # 如果第一次认证失败，尝试另一种认证方式
        try:
            if auth_type == "service":
                tenant_context = await get_jwt_tenant_context(authorization)
                return AuthContext(tenant_context=tenant_context)
            else:
                service_context = await get_service_context(authorization)
                return AuthContext(service_context=service_context)
        except HTTPException as e:
            # 两种认证方式都失败
            logger.warning(f"统一认证失败: {e.detail}")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "AUTHENTICATION_FAILED",
                    "message": "认证失败，请检查JWT token有效性"
                }
            )


def require_tenant_access(tenant_id: Optional[str] = None):
    """
    要求具有租户访问权限的认证依赖
    
    参数:
        tenant_id: 可选的租户ID，如果指定则验证访问权限
    
    返回:
        认证上下文依赖函数
    """
    async def tenant_access_dependency(
        auth_context: AuthContext = Depends(get_unified_auth_context)
    ) -> AuthContext:
        if tenant_id and not auth_context.can_access_tenant(tenant_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "TENANT_ACCESS_DENIED",
                    "message": f"无权访问租户: {tenant_id}",
                    "current_tenant": auth_context.tenant_id
                }
            )
        return auth_context
    
    return tenant_access_dependency


def require_device_access(device_id: str):
    """
    要求具有设备访问权限的认证依赖
    
    参数:
        device_id: 设备ID
    
    返回:
        认证上下文依赖函数
    """
    async def device_access_dependency(
        auth_context: AuthContext = Depends(get_unified_auth_context)
    ) -> AuthContext:
        if not auth_context.can_access_device(device_id):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "DEVICE_ACCESS_DENIED",
                    "message": f"无权访问设备: {device_id}"
                }
            )
        return auth_context
    
    return device_access_dependency


# 便捷的依赖别名
UnifiedAuth = Depends(get_unified_auth_context)
get_auth_context = get_unified_auth_context
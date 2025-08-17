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
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Header, Depends
from pydantic import BaseModel, Field

from config.settings import settings
from utils import get_component_logger, get_current_datetime, format_datetime, format_datetime_int
from .key_manager import key_manager


class ServiceContext(BaseModel):
    """
    服务间认证上下文
    
    从JWT token中提取的服务认证信息，用于后端服务
    向MAS系统的API调用授权验证。
    """
    
    # JWT标准字段
    sub: str = Field(description="主体，固定为'backend-service'")
    iss: str = Field(description="JWT颁发者")
    aud: str = Field(description="JWT受众")
    exp: datetime = Field(description="JWT过期时间")
    iat: datetime = Field(description="JWT颁发时间")
    jti: str = Field(description="JWT唯一标识")
    
    # 服务权限
    scopes: List[str] = Field(default=[], description="服务权限范围列表")
    
    # 验证元数据
    token_source: str = Field(description="Token来源")
    verification_timestamp: datetime = Field(description="验证时间戳")
    
    def has_scope(self, scope: str) -> bool:
        """
        检查是否具有指定权限范围
        """
        return scope in self.scopes
    
    def is_admin(self) -> bool:
        """
        检查是否具有管理员权限
        """
        return "backend:admin" in self.scopes


class ServiceVerificationResult(BaseModel):
    """
    服务JWT验证结果模型
    
    JWT token验证的完整结果，包含验证状态、
    服务上下文和错误信息。
    """
    
    is_valid: bool = Field(description="是否验证成功")
    service_context: Optional[ServiceContext] = Field(
        None, 
        description="验证成功时的服务上下文"
    )
    error_code: Optional[str] = Field(None, description="错误代码")
    error_message: Optional[str] = Field(None, description="错误消息")
    verification_details: Dict[str, Any] = Field(
        default_factory=dict, 
        description="验证详细信息"
    )

logger = get_component_logger(__name__, "JWTAuth")


async def verify_service_jwt_token(token: str) -> ServiceVerificationResult:
    """
    验证服务间JWT token
    
    参数:
        token: JWT token字符串
        
    返回:
        ServiceVerificationResult: 验证结果
    """
    try:
        # 配置检查
        if not settings.app_key:
            return ServiceVerificationResult(
                is_valid=False,
                error_code="SERVICE_AUTH_NOT_CONFIGURED",
                error_message="服务认证未配置",
                verification_details={"missing": "app_key"}
            )
        
        # 获取公钥用于验证
        public_key = key_manager.get_public_key(settings.app_key)
        if not public_key:
            return ServiceVerificationResult(
                is_valid=False,
                error_code="SERVICE_KEY_NOT_FOUND",
                error_message="服务密钥对未找到或已过期",
                verification_details={"app_key": settings.app_key}
            )
        
        # 验证JWT签名和声明
        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=settings.app_jwt_issuer,
                audience=settings.app_jwt_audience,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "jti"],
                    "verify_exp": True,
                    "verify_iat": True,
                }
            )
        except jwt.ExpiredSignatureError:
            return ServiceVerificationResult(
                is_valid=False,
                error_code="SERVICE_TOKEN_EXPIRED",
                error_message="服务JWT token已过期",
                verification_details={"token_type": "service"}
            )
        except jwt.InvalidTokenError as e:
            return ServiceVerificationResult(
                is_valid=False,
                error_code="INVALID_SERVICE_TOKEN",
                error_message=f"服务JWT token验证失败: {str(e)}",
                verification_details={"jwt_error": str(e), "token_type": "service"}
            )
        
        # 验证主体必须是backend-service
        if payload.get("sub") != "backend-service":
            return ServiceVerificationResult(
                is_valid=False,
                error_code="INVALID_SERVICE_SUBJECT",
                error_message="服务token主体无效",
                verification_details={"expected_sub": "backend-service", "actual_sub": payload.get("sub")}
            )
        
        # 构建服务上下文
        current_time = get_current_datetime()
        issued_at = format_datetime_int(payload.get("iat"))
        exp_time = format_datetime_int(payload.get("exp"))
        
        service_context = ServiceContext(
            sub=payload.get("sub"),
            iss=payload.get("iss"),
            aud=payload.get("aud"),
            exp=exp_time,
            iat=issued_at,
            jti=payload.get("jti"),
            scopes=payload.get("scope", []),
            token_source="Service Authorization Header",
            verification_timestamp=current_time
        )
        
        return ServiceVerificationResult(
            is_valid=True,
            service_context=service_context,
            verification_details={
                "verification_time": current_time.isoformat(),
                "token_age_seconds": (current_time - issued_at).total_seconds(),
                "token_type": "service"
            }
        )
        
    except Exception as e:
        logger.error(f"服务JWT验证过程异常: {e}", exc_info=True)
        return ServiceVerificationResult(
            is_valid=False,
            error_code="SERVICE_VERIFICATION_ERROR",
            error_message=f"服务JWT验证过程发生异常: {str(e)}",
            verification_details={"exception": str(e), "token_type": "service"}
        )


async def get_service_context(
    authorization: Optional[str] = Header(None)
) -> ServiceContext:
    """
    FastAPI依赖：从服务JWT token中提取服务上下文
    
    参数:
        authorization: Authorization header值
        
    返回:
        ServiceContext: 验证成功的服务上下文
        
    异常:
        HTTPException: 认证失败时抛出401错误
    """
    # 检查Authorization header
    if not authorization:
        logger.warning("服务认证缺少Authorization header")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_SERVICE_AUTHORIZATION",
                "message": "缺少服务认证Authorization header"
            }
        )
    
    # 解析Bearer token
    auth_parts = authorization.split()
    if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
        logger.warning(f"无效的服务Authorization格式: {authorization[:50]}...")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_SERVICE_AUTHORIZATION_FORMAT",
                "message": "服务Authorization header格式必须为: Bearer <token>"
            }
        )
    
    token = auth_parts[1]
    
    # 基本token格式检查
    if len(token) < 50:  # JWT tokens通常很长
        logger.warning("服务Token长度异常")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_SERVICE_TOKEN_FORMAT",
                "message": "服务Token格式无效"
            }
        )
    
    # 验证服务JWT token
    try:
        verification_result = await verify_service_jwt_token(token)
        
        if not verification_result.is_valid:
            logger.warning(
                f"服务JWT验证失败: {verification_result.error_code} - "
                f"{verification_result.error_message}"
            )
            
            raise HTTPException(
                status_code=401,
                detail={
                    "error": verification_result.error_code,
                    "message": verification_result.error_message
                }
            )
        
        return verification_result.service_context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"服务JWT认证异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SERVICE_AUTHENTICATION_ERROR",
                "message": "服务认证暂时不可用"
            }
        )


def require_service_scopes(*scopes: str):
    """服务权限依赖装饰器"""
    async def scope_dependency(
        service_context: ServiceContext = Depends(get_service_context)
    ) -> ServiceContext:
        missing_scopes = [
            scope for scope in scopes
            if not service_context.has_scope(scope)
        ]
        
        if missing_scopes:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "INSUFFICIENT_SERVICE_SCOPES",
                    "message": f"缺少必需的服务权限: {', '.join(missing_scopes)}",
                    "required_scopes": list(scopes),
                    "current_scopes": service_context.scopes
                }
            )
        
        return service_context
    
    return scope_dependency
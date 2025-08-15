"""
JWT认证数据模型

该模块定义JWT认证系统使用的数据模型，包括租户上下文、
配置管理和权限控制相关的数据结构。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class TenantRole(str, Enum):
    """租户角色枚举"""
    ADMIN = "admin"
    OPERATOR = "operator" 
    VIEWER = "viewer"
    API_USER = "api_user"


class TenantConfig(BaseModel):
    """
    租户配置模型
    
    存储租户的业务配置信息，包括品牌设置、AI偏好和功能配置。
    """
    
    tenant_id: str = Field(description="租户标识符")
    tenant_name: str = Field(description="租户名称")
    
    # 业务配置
    brand_settings: Dict[str, Any] = Field(
        default_factory=dict, description="品牌设置（logo、颜色、主题等）"
    )
    ai_model_preferences: Dict[str, str] = Field(
        default_factory=dict, description="AI模型偏好设置"
    )
    compliance_settings: Dict[str, bool] = Field(
        default_factory=dict, description="合规设置（GDPR、数据保留等）"
    )
    feature_flags: Dict[str, bool] = Field(
        default_factory=dict, description="功能开关"
    )
    
    # 访问控制
    allowed_origins: List[str] = Field(default=[], description="允许的来源域名")
    rate_limit_config: Dict[str, int] = Field(
        default_factory=lambda: {"per_minute": 100, "per_hour": 3600, "per_day": 10000},
        description="速率限制配置"
    )
    
    # 功能开关
    enable_audit_logging: bool = Field(default=True, description="是否启用审计日志")
    enable_rate_limiting: bool = Field(default=True, description="是否启用速率限制")
    enable_device_validation: bool = Field(default=True, description="是否启用设备验证")
    
    # 状态信息
    is_active: bool = Field(default=True, description="租户是否激活")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")
    
    # 统计信息
    last_access: Optional[datetime] = Field(None, description="最后访问时间")
    total_requests: int = Field(default=0, description="总请求数")


class ServiceContext(BaseModel):
    """
    服务间认证上下文信息
    
    该模型包含从服务JWT token中提取的认证信息，
    用于后端服务向MAS系统的API调用授权。
    """
    
    # JWT标准字段
    sub: str = Field(description="主体，固定为'backend-service'")
    iss: str = Field(description="颁发者")
    aud: str = Field(description="受众")
    exp: datetime = Field(description="过期时间")
    iat: datetime = Field(description="颁发时间")
    jti: str = Field(description="JWT ID")
    
    # 服务权限
    scopes: List[str] = Field(default=[], description="服务权限范围")
    
    # 验证元数据
    token_source: str = Field(description="Token来源")
    verification_timestamp: datetime = Field(description="验证时间戳")
    
    def has_scope(self, scope: str) -> bool:
        """检查是否具有指定权限范围"""
        return scope in self.scopes
    
    def is_admin(self) -> bool:
        """检查是否具有管理员权限"""
        return "backend:admin" in self.scopes


class ServiceVerificationResult(BaseModel):
    """服务JWT验证结果模型"""
    
    is_valid: bool = Field(description="是否验证成功")
    service_context: Optional[ServiceContext] = Field(None, description="服务上下文")
    error_code: Optional[str] = Field(None, description="错误代码")
    error_message: Optional[str] = Field(None, description="错误消息")
    verification_details: Dict[str, Any] = Field(
        default_factory=dict, 
        description="验证详细信息"
    )


class SecurityAuditLog(BaseModel):
    """安全审计日志模型"""
    
    log_id: str = Field(description="日志ID")
    tenant_id: str = Field(description="租户ID")
    
    # 事件信息
    event_type: str = Field(description="事件类型")
    event_timestamp: datetime = Field(description="事件时间")
    
    # 请求信息
    client_ip: str = Field(description="客户端IP")
    user_agent: Optional[str] = Field(None, description="用户代理")
    request_id: Optional[str] = Field(None, description="请求ID")
    
    # 认证信息
    jwt_subject: Optional[str] = Field(None, description="JWT主体")
    jwt_issuer: Optional[str] = Field(None, description="JWT颁发者")
    authentication_result: str = Field(description="认证结果")
    
    # 详细信息
    details: Dict[str, Any] = Field(default_factory=dict, description="事件详细信息")
    risk_level: str = Field(
        default="low", 
        description="风险级别", 
        pattern="^(low|medium|high|critical)$"
    )
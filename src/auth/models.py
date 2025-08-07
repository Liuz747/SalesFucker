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


class JWTTenantContext(BaseModel):
    """
    JWT验证后的租户上下文信息
    
    该模型包含从JWT token中提取和验证的租户身份信息，
    用于后续的授权和资源访问控制。
    """
    
    tenant_id: str = Field(description="租户标识符")
    
    # JWT标准字段
    sub: str = Field(description="主体（subject），通常是用户或应用ID")
    iss: str = Field(description="颁发者（issuer）")
    aud: str = Field(description="受众（audience）")
    exp: datetime = Field(description="过期时间")
    iat: datetime = Field(description="颁发时间")
    jti: str = Field(description="JWT ID，用于唯一标识")
    
    # 租户相关权限
    roles: List[TenantRole] = Field(default=[], description="租户角色列表")
    permissions: List[str] = Field(default=[], description="权限列表")
    
    # 访问控制
    allowed_agents: Optional[List[str]] = Field(None, description="允许访问的智能体类型")
    allowed_devices: Optional[List[str]] = Field(None, description="允许访问的设备ID列表")
    
    # 配额限制
    rate_limit_per_minute: int = Field(default=100, description="每分钟请求限制")
    daily_quota: int = Field(default=10000, description="每日配额")
    
    # 租户元信息
    tenant_name: Optional[str] = Field(None, description="租户名称")
    tenant_type: Optional[str] = Field(None, description="租户类型")
    
    # 验证元数据
    token_source: str = Field(description="Token来源（Authorization header）")
    verification_timestamp: datetime = Field(description="验证时间戳")
    
    def has_permission(self, permission: str) -> bool:
        """检查是否具有指定权限"""
        return permission in self.permissions
    
    def has_role(self, role: TenantRole) -> bool:
        """检查是否具有指定角色"""
        return role in self.roles
    
    def can_access_agent(self, agent_id: str) -> bool:
        """检查是否可以访问指定智能体"""
        if not self.allowed_agents:
            return True  # 无限制时允许所有访问
        
        # 提取智能体类型（去除租户后缀）
        agent_type = agent_id.split('_')[0] if '_' in agent_id else agent_id
        return agent_type in self.allowed_agents
    
    def can_access_device(self, device_id: str) -> bool:
        """检查是否可以访问指定设备"""
        if not self.allowed_devices:
            return True  # 无限制时允许所有访问
        return device_id in self.allowed_devices


class TenantConfig(BaseModel):
    """
    租户配置模型
    
    存储租户的认证配置信息，包括JWT公钥和访问控制设置。
    """
    
    tenant_id: str = Field(description="租户标识符")
    tenant_name: str = Field(description="租户名称")
    
    # JWT配置
    jwt_public_key: str = Field(description="RSA公钥（PEM格式）")
    jwt_algorithm: str = Field(default="RS256", description="JWT签名算法")
    jwt_issuer: str = Field(description="期望的JWT颁发者")
    jwt_audience: str = Field(description="期望的JWT受众")
    
    # 安全配置
    token_expiry_hours: int = Field(default=24, description="Token有效期（小时）") 
    max_token_age_minutes: int = Field(default=5, description="Token最大延迟（分钟）")
    
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


class JWTVerificationResult(BaseModel):
    """JWT验证结果模型"""
    
    is_valid: bool = Field(description="是否验证成功")
    tenant_context: Optional[JWTTenantContext] = Field(None, description="租户上下文")
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
        regex="^(low|medium|high|critical)$"
    )
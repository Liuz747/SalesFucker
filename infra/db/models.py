"""
数据库模型定义

该模块定义租户管理相关的SQLAlchemy数据库模型。
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

from infra.auth.models import TenantConfig, SecurityAuditLog

Base = declarative_base()


class TenantModel(Base):
    """
    租户配置数据库模型
    
    对应TenantConfig业务模型，用于PostgreSQL存储。
    """
    __tablename__ = "tenants"
    
    # 主键和基本标识
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_name = Column(String(500), nullable=False)
    
    # 业务配置（使用JSONB存储复杂配置）
    brand_settings = Column(JSONB, nullable=False, default=dict)
    ai_model_preferences = Column(JSONB, nullable=False, default=dict)
    compliance_settings = Column(JSONB, nullable=False, default=dict)
    feature_flags = Column(JSONB, nullable=False, default=dict)
    
    # 访问控制
    allowed_origins = Column(JSONB, nullable=False, default=list)
    rate_limit_config = Column(JSONB, nullable=False, default=dict)
    
    # 功能开关
    enable_audit_logging = Column(Boolean, nullable=False, default=True)
    enable_rate_limiting = Column(Boolean, nullable=False, default=True)
    enable_device_validation = Column(Boolean, nullable=False, default=True)
    
    # 状态信息
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # 统计信息
    last_access = Column(DateTime(timezone=True), nullable=True)
    total_requests = Column(Integer, nullable=False, default=0)
    
    # 数据库索引
    __table_args__ = (
        Index('idx_tenant_id', 'tenant_id'),
        Index('idx_tenant_active', 'is_active'),
        Index('idx_tenant_updated', 'updated_at'),
    )
    
    def to_business_model(self) -> TenantConfig:
        """
        转换为业务模型
        
        返回:
            TenantConfig: 业务模型实例
        """
        return TenantConfig(
            tenant_id=self.tenant_id,
            tenant_name=self.tenant_name,
            brand_settings=self.brand_settings or {},
            ai_model_preferences=self.ai_model_preferences or {},
            compliance_settings=self.compliance_settings or {},
            feature_flags=self.feature_flags or {},
            allowed_origins=self.allowed_origins or [],
            rate_limit_config=self.rate_limit_config or {
                "per_minute": 100, 
                "per_hour": 3600, 
                "per_day": 10000
            },
            enable_audit_logging=self.enable_audit_logging,
            enable_rate_limiting=self.enable_rate_limiting,
            enable_device_validation=self.enable_device_validation,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_access=self.last_access,
            total_requests=self.total_requests
        )
    
    @classmethod
    def from_business_model(cls, config: TenantConfig) -> "TenantModel":
        """
        从业务模型创建数据库模型
        
        参数:
            config: TenantConfig业务模型
            
        返回:
            TenantModel: 数据库模型实例
        """
        return cls(
            tenant_id=config.tenant_id,
            tenant_name=config.tenant_name,
            brand_settings=config.brand_settings,
            ai_model_preferences=config.ai_model_preferences,
            compliance_settings=config.compliance_settings,
            feature_flags=config.feature_flags,
            allowed_origins=config.allowed_origins,
            rate_limit_config=config.rate_limit_config,
            enable_audit_logging=config.enable_audit_logging,
            enable_rate_limiting=config.enable_rate_limiting,
            enable_device_validation=config.enable_device_validation,
            is_active=config.is_active,
            created_at=config.created_at,
            updated_at=config.updated_at,
            last_access=config.last_access,
            total_requests=config.total_requests
        )
    
    def update_from_business_model(self, config: TenantConfig) -> None:
        """
        从业务模型更新数据库模型
        
        参数:
            config: TenantConfig业务模型
        """
        self.tenant_name = config.tenant_name
        self.brand_settings = config.brand_settings
        self.ai_model_preferences = config.ai_model_preferences
        self.compliance_settings = config.compliance_settings
        self.feature_flags = config.feature_flags
        self.allowed_origins = config.allowed_origins
        self.rate_limit_config = config.rate_limit_config
        self.enable_audit_logging = config.enable_audit_logging
        self.enable_rate_limiting = config.enable_rate_limiting
        self.enable_device_validation = config.enable_device_validation
        self.is_active = config.is_active
        self.last_access = config.last_access
        self.total_requests = config.total_requests
        # updated_at 会自动更新


class SecurityAuditLogModel(Base):
    """
    安全审计日志数据库模型
    
    对应SecurityAuditLog业务模型，用于PostgreSQL存储。
    """
    __tablename__ = "security_audit_logs"
    
    # 主键和标识
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # 事件信息
    event_type = Column(String(100), nullable=False, index=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 请求信息
    client_ip = Column(String(45), nullable=False)  # 支持IPv6
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    
    # 认证信息
    jwt_subject = Column(String(255), nullable=True)
    jwt_issuer = Column(String(255), nullable=True)
    authentication_result = Column(String(50), nullable=False)
    
    # 详细信息和风险级别
    details = Column(JSONB, nullable=False, default=dict)
    risk_level = Column(String(20), nullable=False, default="low", index=True)
    
    # 创建时间（自动设置）
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # 数据库索引
    __table_args__ = (
        Index('idx_audit_tenant_event', 'tenant_id', 'event_type'),
        Index('idx_audit_timestamp', 'event_timestamp'),
        Index('idx_audit_risk', 'risk_level'),
        Index('idx_audit_client_ip', 'client_ip'),
    )
    
    def to_business_model(self) -> SecurityAuditLog:
        """
        转换为业务模型
        
        返回:
            SecurityAuditLog: 业务模型实例
        """
        return SecurityAuditLog(
            log_id=self.log_id,
            tenant_id=self.tenant_id,
            event_type=self.event_type,
            event_timestamp=self.event_timestamp,
            client_ip=self.client_ip,
            user_agent=self.user_agent,
            request_id=self.request_id,
            jwt_subject=self.jwt_subject,
            jwt_issuer=self.jwt_issuer,
            authentication_result=self.authentication_result,
            details=self.details or {},
            risk_level=self.risk_level
        )
    
    @classmethod
    def from_business_model(cls, log: SecurityAuditLog) -> "SecurityAuditLogModel":
        """
        从业务模型创建数据库模型
        
        参数:
            log: SecurityAuditLog业务模型
            
        返回:
            SecurityAuditLogModel: 数据库模型实例
        """
        return cls(
            log_id=log.log_id,
            tenant_id=log.tenant_id,
            event_type=log.event_type,
            event_timestamp=log.event_timestamp,
            client_ip=log.client_ip,
            user_agent=log.user_agent,
            request_id=log.request_id,
            jwt_subject=log.jwt_subject,
            jwt_issuer=log.jwt_issuer,
            authentication_result=log.authentication_result,
            details=log.details,
            risk_level=log.risk_level
        )

"""
租户管理数据模型

包含租户管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- TenantRole: 租户角色枚举
- TenantOrm: 租户数据库模型
"""

from enum import StrEnum

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from models.base import Base


class TenantRole(StrEnum):
    """租户角色枚举"""
    ADMIN = "admin"          # 管理员
    OPERATOR = "operator"    # 操作员
    VIEWER = "viewer"        # 查看者
    API_USER = "api_user"    # API用户


class TenantOrm(Base):
    """
    租户数据库模型
    
    对应实际数据库中的tenant表结构
    """
    __tablename__ = "tenants"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 基本信息
    tenant_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_name = Column(String(500), nullable=False)
    status = Column(Integer, nullable=False, default=1)
    
    # 业务信息
    industry = Column(Integer, nullable=False)
    company_size = Column(Integer, nullable=True)
    area_id = Column(Integer, nullable=False)
    user_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime, nullable=True)
    
    # 审计字段
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        onupdate=func.now()
    )
    creator = Column(Integer, nullable=False)
    editor = Column(Integer, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)
    
    # 扩展配置（新增JSONB字段用于存储复杂配置）
    feature_flags = Column(JSONB, nullable=True, default=dict)
    
    # 数据库索引优化
    __table_args__ = (
        Index('idx_tenant_id', 'tenant_id'),
        Index('idx_tenant_status', 'status'),
        Index('idx_tenant_industry', 'industry'),
        Index('idx_tenant_deleted', 'deleted'),
    )
    

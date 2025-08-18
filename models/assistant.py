"""
助理数据模型

todo
包含助理管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- TenantRole: 租户角色枚举
- TenantConfig: 租户配置业务模型 
- SecurityAuditLog: 安全审计日志
- TenantModel: 租户数据库模型
- SecurityAuditLogModel: 审计日志数据库模型
"""

# todo 所有的注释都需要修改

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Index
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from models.base import Base

#
# class TenantRole(StrEnum):
#     """租户角色枚举"""
#     ADMIN = "admin"          # 管理员
#     OPERATOR = "operator"    # 操作员
#     VIEWER = "viewer"        # 查看者
#     API_USER = "api_user"    # API用户


class AssistantConfig(BaseModel):
    """
    租户配置业务模型
    
    存储租户的完整业务配置信息，包括品牌设置、AI偏好、
    功能开关、访问控制等。用于业务逻辑处理。
    """
    
    # 基本信息
    tenant_id: str = Field(description="租户 ID")
    tenant_name: str = Field(description="租户名称")

    assistant_id: str = Field(description="助理 ID")
    assistant_name: str = Field(description="助理名称")


    # 状态信息
    is_active: bool = Field(default=True, description="租户是否激活")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后更新时间")
    #
    # # 统计信息
    # last_access: Optional[datetime] = Field(None, description="最后访问时间")
    # total_requests: int = Field(default=0, description="总请求数")


class AssistantModel(Base):
    """
    租户配置数据库模型
    
    对应TenantConfig业务模型的PostgreSQL存储结构。
    使用JSONB字段存储复杂配置，支持高效查询和索引。
    """
    __tablename__ = "assistant"
    
    # 主键和基本标识
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), unique=True, nullable=False, index=True)
    tenant_name = Column(String(500), nullable=False)
    assistant_id = Column(String(255), unique=True, nullable=False, index=True)
    assistant_name = Column(String(500), nullable=False)


    
    # 状态信息
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(),
        # postgre 不支持 on update, 需要触发器，暂不创建
        onupdate=func.now()
    )


    # todo 索引需要重写
    # 数据库索引优化
    __table_args__ = (
        Index('idx_tenant_id', 'tenant_id'),
        Index('idx_tenant_active', 'is_active'),
        Index('idx_tenant_updated', 'updated_at'),
    )
    
    def to_business_model(self) -> AssistantConfig:
        """
        转换为业务模型
        
        将数据库模型转换为业务逻辑使用的Pydantic模型，
        处理默认值和数据类型转换。
        
        返回:
            TenantConfig: 业务模型实例
        """
        return AssistantConfig(
            tenant_id=self.tenant_id,
            tenant_name=self.tenant_name,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
    
    @classmethod
    def from_business_model(cls, config: AssistantConfig) -> "AssistantModel":
        """
        从业务模型创建数据库模型
        
        将业务模型转换为数据库模型实例，用于数据持久化。
        
        参数:
            config: TenantConfig业务模型实例
            
        返回:
            TenantModel: 数据库模型实例
        """
        return cls(
            tenant_id=config.tenant_id,
            tenant_name=config.tenant_name,

            is_active=config.is_active,
            created_at=config.created_at,
            updated_at=config.updated_at,
            # last_access=config.last_access,
            # total_requests=config.total_requests
        )
    
    def update_from_business_model(self, config: AssistantConfig) -> None:
        """
        从业务模型更新数据库模型
        
        使用业务模型的数据更新当前数据库模型实例。
        updated_at字段会自动更新。
        
        参数:
            config: TenantConfig业务模型实例
        """

        self.tenant_id = config.tenant_id
        self.tenant_name = config.tenant_name
        self.assistant_id = config.assistant_id
        self.assistant_name = config.assistant_name
        self.is_active = config.is_active


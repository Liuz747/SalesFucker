"""
租户管理数据模型

包含租户管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- TenantRole: 租户角色枚举
- TenantModel: 租户配置业务模型
- TenantOrm: 租户数据库模型
"""
import uuid

from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
from enum import StrEnum
from typing import Dict, Optional

from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Index
)
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from models.base import Base


class TenantRole(StrEnum):
    """租户角色枚举"""
    ADMIN = "admin"          # 管理员
    OPERATOR = "operator"    # 操作员
    VIEWER = "viewer"        # 查看者
    API_USER = "api_user"    # API用户
    # todo merge 测试
#
# class TenantModel(BaseModel):
#     """
#     租户配置业务模型
#
#     存储租户的完整业务配置信息，包括品牌设置、AI偏好、
#     功能开关、访问控制等。用于业务逻辑处理。
#     """
#
#     # 基本信息
#     tenant_id: str = Field(description="租户标识符")
#     tenant_name: str = Field(description="租户名称")
#     status: int = Field(default=1, description="状态：1-活跃，0-禁用")
#
#     # 业务信息
#     industry: int = Field(default=1, description="行业类型：1-美容诊所，2-化妆品公司等")
#     company_size: Optional[int] = Field(default=1, description="公司规模：1-小型，2-中型，3-大型")
#     area_id: int = Field(default=1, description="地区ID")
#     user_count: int = Field(default=0, description="用户数量")
#     expires_at: Optional[datetime] = Field(None, description="过期时间")
#
#     # 审计字段
#     creator: int = Field(default=1, description="创建者ID")
#     editor: Optional[int] = Field(None, description="编辑者ID")
#     deleted: bool = Field(default=False, description="删除标记")
#     created_at: Optional[datetime] = Field(None, description="创建时间")
#     updated_at: Optional[datetime] = Field(None, description="最后更新时间")
#
#     # 业务配置
#     feature_flags: Dict[str, bool] = Field(
#         default_factory=dict,
#         description="功能开关配置"
#     )
#
#     def to_orm(self) -> 'TenantOrm':
#         """
#         转换为数据库模型
#
#         将业务模型转换为数据库模型实例，用于数据持久化。
#         处理字段映射和数据类型转换。
#
#         返回:
#             TenantOrm: 数据库模型实例
#         """
#         return TenantOrm(
#             tenant_id=self.tenant_id,
#             tenant_name=self.tenant_name,
#             status=self.status,
#             industry=self.industry,
#             company_size=self.company_size,
#             area_id=self.area_id,
#             user_count=self.user_count,
#             expires_at=self.expires_at,
#             feature_flags=self.feature_flags,
#             creator=self.creator,
#             editor=self.editor,
#             deleted=self.deleted,
#             created_at=func.now(),
#             updated_at=func.now()
#         )
#

class TenantOrm(Base):
    """
    租户数据库模型
    
    对应实际数据库中的tenant表结构
    """
    __tablename__ = "tenants"
    
    # 主键
    # id = Column(uuid.UUID, primary_key=True, autoincrement=True)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 基本信息
    tenant_id = Column(String(255), primary_key=True, nullable=False)
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
    is_active = Column(Boolean, nullable=False, default=True)

    # 扩展配置（新增JSONB字段用于存储复杂配置）
    feature_flags = Column(JSONB, nullable=True, default=dict)
    
    # 数据库索引优化
    __table_args__ = (
        Index('idx_tenant_status', 'status'),
        Index('idx_tenant_industry', 'industry'),
        Index('idx_tenant_deleted', 'deleted'),
        Index('idx_tenant_is_active', 'is_active'),
    )
    # todo merge 测试
    # def to_model(self) -> TenantModel:
    #     """
    #     转换为业务模型
    #
    #     将数据库模型转换为业务逻辑使用的Pydantic模型，
    #     处理默认值和数据类型转换。
    #
    #     返回:
    #         TenantModel: 业务模型实例
    #     """
    #     return TenantModel(
    #         tenant_id=self.tenant_id,
    #         tenant_name=self.tenant_name,
    #         status=self.status,
    #         industry=self.industry,
    #         company_size=self.company_size,
    #         area_id=self.area_id,
    #         user_count=self.user_count,
    #         expires_at=self.expires_at,
    #         feature_flags=self.feature_flags or {},
    #         creator=self.creator,
    #         editor=self.editor,
    #         deleted=self.deleted,
    #         created_at=self.created_at,
    #         updated_at=self.updated_at
    #     )
    #
    # def update(self, config: TenantModel):
    #     """
    #     从业务配置更新数据库模型
    #
    #     使用业务配置更新现有数据库模型实例，保持数据库追踪状态。
    #
    #     参数:
    #         config: TenantModel业务配置实例
    #     """
    #     self.tenant_name = config.tenant_name
    #     self.status = config.status
    #     self.industry = config.industry
    #     self.company_size = config.company_size
    #     self.area_id = config.area_id
    #     self.user_count = config.user_count
    #     self.expires_at = config.expires_at
    #     self.feature_flags = config.feature_flags
    #     self.updated_at = func.now()

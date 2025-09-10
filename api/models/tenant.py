"""
租户管理数据模型

包含租户管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- TenantRole: 租户角色枚举
- TenantModel: 租户配置业务模型
- TenantOrm: 租户数据库模型
"""

from enum import StrEnum

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Index, Enum, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class TenantRole(StrEnum):
    """租户角色枚举"""
    ADMIN = "admin"          # 管理员
    OPERATOR = "operator"    # 操作员
    VIEWER = "viewer"        # 查看者
    EDITOR = "editor"        # 编辑者


class TenantStatus(StrEnum):
    """租户状态枚举"""
    ACTIVE = "active"          # 活跃
    BANNED = "banned"          # 禁用
    CLOSED = "closed"          # 关闭


class TenantOrm(Base):
    """
    租户数据库模型
    
    对应实际数据库中的tenant表结构
    """
    __tablename__ = "tenants"
    
    # 基本信息
    tenant_id = Column(String(64), primary_key=True)
    tenant_name = Column(String(255), nullable=False)
    status = Column(Enum(TenantStatus, name='tenant_status'), nullable=False, default=TenantStatus.ACTIVE)
    
    # 业务信息
    industry = Column(String(64))
    company_size = Column(Integer)
    area_id = Column(String(64))
    user_count = Column(Integer, default=0)
    expires_at = Column(DateTime)
    
    # 审计字段
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )
    creator = Column(Integer)
    editor = Column(Integer)
    is_active = Column(Boolean, nullable=False, default=True)

    # 扩展配置（新增JSONB字段用于存储复杂配置）
    feature_flags = Column(JSONB, default=dict)
    
    # 数据库索引优化
    __table_args__ = (
        Index('idx_tenant_status', 'status'),
        Index('idx_tenant_industry', 'industry'),
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

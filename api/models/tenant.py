"""
租户管理数据模型

包含租户管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- TenantRole: 租户角色枚举
- TenantModel: 租户配置业务模型
- TenantOrm: 租户数据库模型
"""

from datetime import datetime
from typing import Optional, Self

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Index, Enum, func
from sqlalchemy.dialects.postgresql import JSONB

from libs.types import AccountStatus
from .base import Base


class TenantOrm(Base):
    """
    租户数据库模型
    
    对应实际数据库中的tenant表结构
    """
    __tablename__ = "tenants"

    # 基本信息
    tenant_id = Column(String(64), primary_key=True)
    tenant_name = Column(String(255), nullable=False)
    status = Column(Enum(AccountStatus, name='tenant_status'), nullable=False, default=AccountStatus.ACTIVE)

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
    features = Column(JSONB, default=dict)

    # 数据库索引优化
    __table_args__ = (
        Index('idx_tenant_status', 'status'),
        Index('idx_tenant_industry', 'industry'),
        Index('idx_tenant_is_active', 'is_active'),
    )


class TenantModel(BaseModel):
    """
    租户配置业务模型
    
    存储租户的完整业务配置信息，包括品牌设置、AI偏好、
    功能开关、访问控制等。用于业务逻辑处理。
    """

    # 基本信息
    tenant_id: str = Field(description="租户标识符")
    tenant_name: str = Field(description="租户名称")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="状态：1-活跃，0-禁用")

    # 业务信息
    industry: str = Field(default=1, description="行业类型：1-美容诊所，2-化妆品公司等")
    company_size: Optional[int] = Field(default=1, description="公司规模：1-小型，2-中型，3-大型")
    area_id: str = Field(default=1, description="地区ID")
    user_count: int = Field(default=0, description="用户数量")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    # 审计字段
    creator: int = Field(default=1, description="创建者ID")
    editor: Optional[int] = Field(None, description="编辑者ID")
    is_active: bool = Field(default=True, description="激活状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")

    # 业务配置
    features: dict[str, bool] = Field(
        default_factory=dict,
        description="功能开关配置"
    )

    @classmethod
    def to_model(cls, tenant_orm: TenantOrm) -> Self:
        return cls(
            tenant_id=tenant_orm.tenant_id,
            tenant_name=tenant_orm.tenant_name,
            status=tenant_orm.status,
            industry=tenant_orm.industry,
            company_size=tenant_orm.company_size,
            area_id=tenant_orm.area_id,
            user_count=tenant_orm.user_count,
            expires_at=tenant_orm.expires_at,
            creator=tenant_orm.creator,
            editor=tenant_orm.editor,
            is_active=tenant_orm.is_active,
            created_at=tenant_orm.created_at,
            updated_at=tenant_orm.updated_at,
            features=tenant_orm.features or {},
        )

    def to_orm(self) -> TenantOrm:
        return TenantOrm(
            tenant_id=self.tenant_id,
            tenant_name=self.tenant_name,
            status=self.status,
            industry=self.industry,
            company_size=self.company_size,
            area_id=self.area_id,
            user_count=self.user_count,
            expires_at=self.expires_at,
            creator=self.creator,
            editor=self.editor,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            features=self.features,
        )

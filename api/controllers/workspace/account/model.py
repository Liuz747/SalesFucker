"""
租户管理数据模型

包含租户管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- Tenant: 租户配置业务模型
"""

from datetime import datetime
from typing import Dict, Optional, Self

from pydantic import BaseModel, Field

from models.tenant import TenantOrm


class Tenant(BaseModel):
    """
    租户配置业务模型
    
    存储租户的完整业务配置信息，包括品牌设置、AI偏好、
    功能开关、访问控制等。用于业务逻辑处理。
    """
    
    # 基本信息
    tenant_id: str = Field(description="租户标识符")
    tenant_name: str = Field(description="租户名称")
    status: int = Field(default=1, description="状态：1-活跃，0-禁用")
    
    # 业务信息
    industry: int = Field(default=1, description="行业类型：1-美容诊所，2-化妆品公司等")
    company_size: Optional[int] = Field(default=1, description="公司规模：1-小型，2-中型，3-大型") 
    area_id: int = Field(default=1, description="地区ID")
    user_count: int = Field(default=0, description="用户数量")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    # 审计字段
    creator: int = Field(default=1, description="创建者ID")
    editor: Optional[int] = Field(None, description="编辑者ID")
    deleted: bool = Field(default=False, description="删除标记")
    is_active: bool = Field(default=True, description="激活状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="最后更新时间")
    
    # 业务配置
    feature_flags: Dict[str, bool] = Field(
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
            deleted=tenant_orm.deleted,
            is_active=tenant_orm.is_active,
            created_at=tenant_orm.created_at,
            updated_at=tenant_orm.updated_at,
            feature_flags=tenant_orm.feature_flags or {},
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
            deleted=self.deleted,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            feature_flags=self.feature_flags,
        )
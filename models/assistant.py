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
from datetime import datetime


#
# class TenantRole(StrEnum):
#     """租户角色枚举"""
#     ADMIN = "admin"          # 管理员
#     OPERATOR = "operator"    # 操作员
#     VIEWER = "viewer"        # 查看者
#     API_USER = "api_user"    # API用户


class AssistantModel(BaseModel):
    """
    租户配置业务模型
    
    存储租户的完整业务配置信息，包括品牌设置、AI偏好、
    功能开关、访问控制等。用于业务逻辑处理。
    """
    # 基本信息
    tenant_id: str = Field(description="租户 ID")
    # tenant_name: str = Field(description="租户名称")
    assistant_id: str = Field(description="助理 ID")
    assistant_name: str = Field(description="助理名称")
    assistant_status: str = Field(description="助理状态枚举")
    personality_type: str = Field(description="助理 个性类型")
    expertise_level: str = Field(description="助理 专业等级")
    sales_style: Dict[str, Any] = Field(
        default_factory=dict, description="销售风格配置（可选，建议使用prompt_config）")
    voice_tone: Dict[str, Any] = Field(
        default_factory=dict, description="语音语调配置（可选，建议使用prompt_config）")
    specializations: List[str] = Field(description="专业领域列表（如：护肤、彩妆、香水等）")
    working_hours: Dict[str, Any] = Field(
        default_factory=dict, description="工作时间配置")
    max_concurrent_customers: int = Field(description="最大并发客户数")
    permissions: List[str] = Field(description="助理权限列表")
    profile: Dict[str, Any] = Field(
        default_factory=dict, description="助理个人资料信息")
    is_active: bool = Field(description="租户是否激活")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后一次更新时间")
    last_active_at: Optional[datetime] = Field(description="")
    registered_devices: List[str] = Field(default=[], description="")


class AssistantOrmModel(Base):
    """
    租户配置数据库模型
    
    对应TenantConfig业务模型的PostgreSQL存储结构。
    使用JSONB字段存储复杂配置，支持高效查询和索引。
    """
    __tablename__ = "assistant"

    # 主键和基本标识
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    # tenant_name = Column(String(500), nullable=False)
    assistant_id = Column(String(255), unique=True, nullable=False, index=True)
    assistant_name = Column(String(500), nullable=False)

    assistant_status = Column(String(500), nullable=False)
    assistant_sex = Column(String(500), nullable=False)
    assistant_phone = Column(String(500), nullable=False)
    assistant_personality_type = Column(String(500), nullable=False)
    assistant_expertise_level = Column(String(500), nullable=False)
    assistant_sales_style = Column(JSONB, nullable=False)
    assistant_voice_tone = Column(JSONB, nullable=False)
    assistant_specializations = Column(JSONB, nullable=False)
    assistant_working_hours = Column(JSONB, nullable=False)
    assistant_max_concurrent_customers = Column(Integer, nullable=False)
    assistant_permissions = Column(JSONB, nullable=False)
    assistant_profile = Column(JSONB, nullable=False)

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
    last_active_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    registered_devices = Column(JSONB, nullable=False)

    # todo 索引需要重写
    # 数据库索引优化
    # __table_args__ = (
    #     Index('idx_tenant_id', 'tenant_id'),
    #     Index('idx_tenant_active', 'is_active'),
    #     Index('idx_tenant_updated', 'updated_at'),
    # )

    @classmethod
    def from_business_model(cls, model: AssistantModel) -> "AssistantOrmModel":
        """
        从业务模型创建数据库模型
        
        将业务模型转换为数据库模型实例，用于数据持久化。
        
        参数:
            config: TenantConfig业务模型实例
            
        返回:
            TenantModel: 数据库模型实例
        """
        return cls(
            tenant_id=model.tenant_id,
            # tenant_name=model.tenant_name,

            # tenant_name = Column(String(500), nullable=False)
            assistant_id=model.assistant_id,
            assistant_name=model.assistant_name,

            assistant_status=model.assistant_status,
            # sex = model.assistant_sex,
            # phone =model.assistant_phone,
            assistant_personality_type=model.personality_type,
            assistant_expertise_level=model.expertise_level,
            assistant_sales_style=model.sales_style,
            assistant_voice_tone=model.voice_tone,
            assistant_specializations=model.specializations,
            assistant_working_hours=model.working_hours,
            assistant_max_concurrent_customers=model.max_concurrent_customers,
            assistant_permissions=model.permissions,
            assistant_profile=model.profile,

            # 状态信息
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_active_at=model.last_active_at,
            registered_devices=model.registered_devices,

        )

    def update_from_business_mode_assistant(self, model: AssistantModel) -> None:
        """
        从业务模型更新数据库模型
        
        使用业务模型的数据更新当前数据库模型实例。
        updated_at字段会自动更新。
        
        参数:
            config: TenantConfig业务模型实例
        """

        self.tenant_id = model.tenant_id
        #   self.tenant_name = Column(String(500), nullable=False)
        self.assistant_id = model.assistant_id
        self.assistant_name = model.assistant_name
        self.assistant_status = model.assistant_status

        # self.sex = model.assistant_sex,
        # self.phone =model.assistant_phone,

        self.assistant_personality_type = model.personality_type
        self.assistant_expertise_level = model.expertise_level
        self.assistant_sales_style = model.sales_style
        self.assistant_voice_tone = model.voice_tone
        self.assistant_specializations = model.specializations
        self.assistant_working_hours = model.working_hours
        self.assistant_max_concurrent_customers = model.max_concurrent_customers
        self.assistant_permissions = model.permissions
        self.assistant_profile = model.profile

        self.is_active = model.is_active
        self.created_at = model.created_at
        self.updated_at = model.updated_at
        self.last_active_at = model.last_active_at
        self.registered_devices = model.registered_devices

    def to_business_model(self) -> AssistantModel:
        """
        转换为业务模型

        将数据库模型转换为业务逻辑使用的Pydantic模型，
        处理默认值和数据类型转换。

        返回:
            TenantConfig: 业务模型实例
        """
        return AssistantModel(
            tenant_id=self.tenant_id,

            # tenant_name = Column(String(500), nullable=False)
            assistant_id=self.assistant_id,
            assistant_name=self.assistant_name,
            # assistant_status_1="123",
            assistant_status=self.assistant_status,
            personality_type=self.assistant_personality_type,
            expertise_level=self.assistant_expertise_level,
            sales_style=self.assistant_sales_style,
            voice_tone=self.assistant_voice_tone,
            specializations=self.assistant_specializations,
            working_hours=self.assistant_working_hours,
            max_concurrent_customers=self.assistant_max_concurrent_customers,
            permissions=self.assistant_permissions,
            profile=self.assistant_profile,

            # 状态信息
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_active_at=self.last_active_at,
            registered_devices=self.registered_devices
        )

"""
助理数据模型

包含助理管理相关的业务模型和数据库模型，支持多租户架构。

主要模型:
"""

# todo 所有的注释都需要修改

from datetime import datetime
from typing import Optional, Any
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from .base import Base
from .prompts import PromptsModel


class AssistantModel(BaseModel):
    """
    租户配置业务模型
    
    存储租户的完整业务配置信息，包括品牌设置、AI偏好、
    功能开关、访问控制等。用于业务逻辑处理。
    """
    # 基本信息
    tenant_id: str = Field(description="租户 ID")
    assistant_id: str = Field(description="助理 ID")
    assistant_name: str = Field(description="助理名称")
    assistant_status: str = Field(description="助理状态枚举")
    personality: str = Field(description="助理 个性类型")
    occupation: str = Field(description="数字员工职业")
    voice_id: str = Field(description="语音克隆配置，使用MiniMax模型")
    industry: str = Field(description="专业领域列表（如：护肤、彩妆、香水等）")
    profile: dict[str, Any] = Field(default_factory=dict, description="助理个人资料信息")
    is_active: Optional[bool] = Field(default=None, description="数字员工是否激活")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后一次更新时间")
    last_active_at: Optional[datetime] = Field(description="")

    prompts_model_list: Optional[PromptsModel] = Field(default=None, description="所属提示词")


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
    assistant_id = Column(String(255), unique=True, nullable=False, index=True)
    assistant_name = Column(String(500), nullable=False)

    assistant_status = Column(String(32), nullable=False)
    assistant_sex = Column(String(32), nullable=True)
    assistant_personality = Column(String(500), nullable=False)
    assistant_occupation = Column(String(100), nullable=False)
    assistant_voice_id = Column(String(50), nullable=False)
    assistant_industry = Column(String(100), nullable=False)
    assistant_profile = Column(JSONB, nullable=False)

    # 状态信息
    is_active = Column(Boolean, nullable=True, default=True)
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
            Tenant: 数据库模型实例
        """
        return cls(
            tenant_id=model.tenant_id,
            assistant_id=model.assistant_id,
            assistant_name=model.assistant_name,
            assistant_status=model.assistant_status,
            # sex = model.assistant_sex,
            # phone =model.assistant_phone,
            assistant_personality=model.personality,
            assistant_occupation=model.occupation,
            assistant_voice_id=model.voice_id,
            assistant_industry=model.industry,
            assistant_profile=model.profile,

            # 状态信息
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_active_at=model.last_active_at
        )

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
            personality=self.assistant_personality,
            occupation=self.assistant_occupation,
            voice_id=self.assistant_voice_id,
            industry=self.assistant_industry,
            profile=self.assistant_profile,

            # 状态信息
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_active_at=self.last_active_at
        )

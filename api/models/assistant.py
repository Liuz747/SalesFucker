"""
助理数据模型

包含助理管理相关的业务模型和数据库模型，支持多租户架构。

主要模型:
- AssistantModel: 助理业务模型（Pydantic），用于业务逻辑处理
- AssistantOrmModel: 助理数据库模型（SQLAlchemy ORM），用于数据持久化
"""

from datetime import datetime
from typing import Optional, Any, Self
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime, Uuid, func, Index, Enum
from sqlalchemy.dialects.postgresql import JSONB

from libs.types import AccountStatus
from .base import Base


class AssistantModel(BaseModel):
    """
    数字员工业务模型

    存储数字员工的完整配置信息，包括基本信息、个性设置、语音配置等。
    用于业务逻辑处理和API响应。
    """
    # 基本信息
    assistant_id: Optional[UUID] = Field(default=None, description="助理 ID（由数据库自动生成）")
    tenant_id: str = Field(description="租户 ID")
    assistant_name: str = Field(description="助理名称")
    nickname: Optional[str] = Field(default=None, description="助理昵称")
    address: Optional[str] = Field(default=None, description="助理地址")
    sex: Optional[str] = Field(default=None, description="助理性别")
    status: AccountStatus = Field(default=AccountStatus.ACTIVE, description="助理状态枚举")
    personality: str = Field(description="助理 个性类型")
    occupation: str = Field(description="数字员工职业")
    industry: str = Field(description="专业领域列表（如：护肤、彩妆、香水等）")
    profile: dict[str, Any] = Field(default_factory=dict, description="助理个人资料信息")
    voice_id: str = Field(description="语音克隆配置，使用MiniMax模型")
    voice_file: Optional[str] = Field(default=None, description="语音文件URL链接")
    is_active: Optional[bool] = Field(default=None, description="数字员工是否激活")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后一次更新时间")
    last_active_at: Optional[datetime] = Field(description="")


class AssistantOrmModel(Base):
    """
    数字员工数据库模型

    对应AssistantModel业务模型的PostgreSQL存储结构。
    使用JSONB字段存储复杂配置，支持高效查询和索引。
    """
    __tablename__ = "assistant"

    # 主键和基本标识
    assistant_id = Column(Uuid, primary_key=True, server_default=func.gen_random_uuid())
    tenant_id = Column(String(64), nullable=False, index=True)
    assistant_name = Column(String(100), nullable=False)
    nickname = Column(String(100))
    address = Column(String(500))
    sex = Column(String(32))
    status = Column(Enum(AccountStatus, name='account_status'), nullable=False, default=AccountStatus.ACTIVE)
    personality = Column(String(500), nullable=False)
    occupation = Column(String(100), nullable=False)
    voice_id = Column(String(50), nullable=False)
    voice_file = Column(String(500))
    industry = Column(String(100), nullable=False)
    profile = Column(JSONB, nullable=False)

    # 状态信息
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 数据库索引优化
    __table_args__ = (
        Index('idx_assistant_is_active', 'is_active'),
        Index('idx_assistant_status', 'status'),
        Index('idx_assistant_updated', 'updated_at'),
    )

    @classmethod
    def to_orm_model(cls, model: AssistantModel) -> Self:
        """
        从业务模型创建数据库模型

        将业务模型转换为数据库模型实例，用于数据持久化。

        参数:
            model: AssistantModel业务模型实例

        返回:
            AssistantOrmModel: 数据库模型实例
        """
        return cls(
            assistant_id=model.assistant_id,
            tenant_id=model.tenant_id,
            assistant_name=model.assistant_name,
            nickname=model.nickname,
            address=model.address,
            sex=model.sex,
            status=model.status,
            personality=model.personality,
            occupation=model.occupation,
            voice_id=model.voice_id,
            voice_file=model.voice_file,
            industry=model.industry,
            profile=model.profile,

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
            AssistantModel: 业务模型实例
        """
        return AssistantModel(
            assistant_id=self.assistant_id,
            tenant_id=self.tenant_id,
            assistant_name=self.assistant_name,
            nickname=self.nickname,
            address=self.address,
            sex=self.sex,
            status=self.status,
            personality=self.personality,
            occupation=self.occupation,
            voice_id=self.voice_id,
            voice_file=self.voice_file,
            industry=self.industry,
            profile=self.profile,

            # 状态信息
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_active_at=self.last_active_at
        )

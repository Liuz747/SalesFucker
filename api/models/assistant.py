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
from sqlalchemy import Column, String, Boolean, DateTime, Uuid, func, Index, JSONB

from .base import Base
from .prompts import PromptsModel


class AssistantModel(BaseModel):
    """
    数字员工业务模型

    存储数字员工的完整配置信息，包括基本信息、个性设置、语音配置等。
    用于业务逻辑处理和API响应。
    """
    # 基本信息
    assistant_id: UUID = Field(description="助理 ID")
    tenant_id: str = Field(description="租户 ID")
    assistant_name: str = Field(description="助理名称")
    nickname: Optional[str] = Field(default=None, description="助理昵称")
    address: Optional[str] = Field(default=None, description="助理地址")
    sex: Optional[str] = Field(default=None, description="助理性别")
    assistant_status: str = Field(description="助理状态枚举")
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

    prompts_model_list: Optional[PromptsModel] = Field(default=None, description="所属提示词")


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

    assistant_status = Column(String(32), nullable=False)
    assistant_sex = Column(String(32))
    assistant_personality = Column(String(500), nullable=False)
    assistant_occupation = Column(String(100), nullable=False)
    assistant_voice_id = Column(String(50), nullable=False)
    voice_file = Column(String(500))
    assistant_industry = Column(String(100), nullable=False)
    assistant_profile = Column(JSONB, nullable=False)

    # 状态信息
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # 数据库索引优化
    __table_args__ = (
        Index('idx_assistant_is_active', 'is_active'),
        Index('idx_assistant_status', 'assistant_status'),
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
            tenant_id=model.tenant_id,
            assistant_id=model.assistant_id,
            assistant_name=model.assistant_name,
            nickname=model.nickname,
            address=model.address,
            sex=model.sex,
            assistant_status=model.assistant_status,
            assistant_personality=model.personality,
            assistant_occupation=model.occupation,
            assistant_voice_id=model.voice_id,
            voice_file=model.voice_file,
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
            AssistantModel: 业务模型实例
        """
        return AssistantModel(
            tenant_id=self.tenant_id,
            assistant_id=self.assistant_id,
            assistant_name=self.assistant_name,
            nickname=self.nickname,
            address=self.address,
            sex=self.sex,
            assistant_status=self.assistant_status,
            personality=self.assistant_personality,
            occupation=self.assistant_occupation,
            voice_id=self.assistant_voice_id,
            voice_file=self.voice_file,
            industry=self.assistant_industry,
            profile=self.assistant_profile,

            # 状态信息
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_active_at=self.last_active_at
        )

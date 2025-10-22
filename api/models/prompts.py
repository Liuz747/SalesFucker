"""
助理数据模型

todo
包含助理管理相关的业务模型和数据库模型，支持多租户架构。
提供租户配置、权限控制、审计日志等完整功能。

主要模型:
- TenantRole: 租户角色枚举
- TenantConfig: 租户配置业务模型 
- SecurityAuditLog: 安全审计日志
- Tenant: 租户数据库模型
- SecurityAuditLogModel: 审计日志数据库模型
"""

# todo 所有的注释都需要修改

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Index, BigInteger
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


class PromptsModel(BaseModel):
    """
    提示词
    """
    # 基本信息
    id: Optional[uuid.UUID] = Field(default=None, description="id")
    tenant_id: str = Field(description="租户 ID")
    assistant_id: str = Field(description="助理 ID")
    personality_prompt: str = Field(description="个性化系统提示词 - 定义智能体性格、语调、行为方式")
    greeting_prompt: Optional[str] = Field(default=None, description="问候提示词 - 定义如何开始对话")
    product_recommendation_prompt: Optional[str] = Field(default=None, description="产品推荐提示词 - 定义如何推荐产品")
    objection_handling_prompt: Optional[str] = Field(default=None, description="异议处理提示词 - 定义如何处理客户异议")
    closing_prompt: Optional[str] = Field(default=None, description="结束对话提示词 - 定义如何结束对话")
    context_instructions: Optional[str] = Field(default=None, description="上下文处理指令 - 如何利用历史对话和客户信息")
    llm_parameters: Dict[str, Any] = Field(description="LLM生成参数配置", default=dict)
    safety_guidelines: List[str] = Field(default_factory=list, description="安全和合规指导原则")
    forbidden_topics: List[str] = Field(description="禁止讨论的话题列表")

    brand_voice: Optional[str] = Field(default=None, description="品牌声音定义 - 品牌特色和价值观")
    product_knowledge: Optional[str] = Field(default=None, description="产品知识要点 - 重点产品信息和卖点")
    version: int = Field(default="1758731200000", description="配置版本")
    is_active: Optional[bool] = Field(default=None, description="租户是否激活")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="最后一次更新时间")

    def to_orm(self) -> 'PromptsOrmModel':
        return PromptsOrmModel(
            tenant_id=self.tenant_id,
            assistant_id=self.assistant_id,
            personality_prompt=self.personality_prompt,
            greeting_prompt=self.greeting_prompt,
            product_recommendation_prompt=self.product_recommendation_prompt,
            objection_handling_prompt=self.tenant_id,
            closing_prompt=self.closing_prompt,
            context_instructions=self.context_instructions,
            llm_parameters=self.llm_parameters,
            safety_guidelines=self.safety_guidelines,
            forbidden_topics=self.forbidden_topics,
            brand_voice=self.brand_voice,
            product_knowledge=self.product_knowledge,
            version=self.version,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


from dataclasses import dataclass, asdict
@dataclass
class PromptsOrmModel(Base):
    """
    租户配置数据库模型

    对应TenantConfig业务模型的PostgreSQL存储结构。
    使用JSONB字段存储复杂配置，支持高效查询和索引。
    """
    __tablename__ = "prompts"

    # 主键和基本标识
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False)
    # tenant_name = Column(String(500), nullable=False)
    assistant_id = Column(String(255), nullable=False)
    # assistant_name = Column(String(500), nullable=False)

    personality_prompt: str = Column(String(5000), nullable=False)
    greeting_prompt: Optional[str] = Column(String(500), nullable=False)
    product_recommendation_prompt: Optional[str] = Column(String(1000), nullable=False)
    objection_handling_prompt: Optional[str] = Column(String(1000), nullable=False)
    closing_prompt: Optional[str] = Column(String(500), nullable=False)
    context_instructions: Optional[str] = Column(String(1000), nullable=False)
    llm_parameters: Dict[str, any] = Column(JSONB, nullable=False)
    safety_guidelines: List[str] = Column(JSONB, nullable=False)
    forbidden_topics: List[str] = Column(JSONB, nullable=False)

    brand_voice: Optional[str] = Column(String(500), nullable=True)
    product_knowledge: Optional[str] = Column(String(2000), nullable=True)
    version: int = Column(BigInteger, nullable=False)

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

    # todo 索引需要重写
    # 数据库索引优化
    # __table_args__ = (
    #     Index('idx_tenant_id', 'tenant_id'),
    #     Index('idx_tenant_active', 'is_active'),
    #     Index('idx_tenant_updated', 'updated_at'),
    # )

    def to_model(self) -> PromptsModel:
        """
        从业务模型更新数据库模型

        使用业务模型的数据更新当前数据库模型实例。
        updated_at字段会自动更新。

        参数:
            config: TenantConfig业务模型实例
        """

        return PromptsModel(
            id=self.id,
            tenant_id=self.tenant_id,
            assistant_id=self.assistant_id,
            personality_prompt=self.personality_prompt,
            greeting_prompt=self.greeting_prompt,
            product_recommendation_prompt=self.product_recommendation_prompt,
            objection_handling_prompt=self.tenant_id,
            closing_prompt=self.closing_prompt,
            context_instructions=self.context_instructions,
            llm_parameters=self.llm_parameters,
            safety_guidelines=self.safety_guidelines,
            forbidden_topics=self.forbidden_topics,
            brand_voice=self.brand_voice,
            product_knowledge=self.product_knowledge,
            version=self.version,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    def copy(self) -> "PromptsOrmModel":
        return PromptsOrmModel(
            tenant_id=self.tenant_id,
            assistant_id=self.assistant_id,
            personality_prompt=self.personality_prompt,
            greeting_prompt=self.greeting_prompt,
            product_recommendation_prompt=self.product_recommendation_prompt,
            objection_handling_prompt=self.tenant_id,
            closing_prompt=self.closing_prompt,
            context_instructions=self.context_instructions,
            llm_parameters=self.llm_parameters,
            safety_guidelines=self.safety_guidelines,
            forbidden_topics=self.forbidden_topics,
            brand_voice=self.brand_voice,
            product_knowledge=self.product_knowledge,
            version=self.version,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

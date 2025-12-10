"""
对话相关业务模型

该模块包含对话业务领域的所有模型，包括Pydantic业务模型和SQLAlchemy ORM模型。
"""

from datetime import datetime
from typing import Optional, Self
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Enum, Integer, String, Uuid, func

from libs.types import Sex
from utils import get_current_datetime
from .base import Base
from .enums import ThreadStatus


class ThreadOrm(Base):
    """线程数据库ORM模型 - 每个线程代表一个客户会话"""

    __tablename__ = "threads"

    thread_id = Column(Uuid, primary_key=True, server_default=func.gen_random_uuid())
    tenant_id = Column(String(64), nullable=False, index=True)
    assistant_id = Column(Uuid, index=True)
    status = Column(Enum(ThreadStatus, name='thread_status'), default=ThreadStatus.IDLE, nullable=False, index=True)
    name = Column(String(128), comment="客户姓名")
    sex = Column(Enum(Sex, name='sex'), comment="客户性别")
    age = Column(Integer, comment="客户年龄")
    phone = Column(String(32), index=True, comment="客户电话")
    occupation = Column(String(128), comment="客户职业")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Thread(BaseModel):
    """对话线程数据模型 - 每个线程代表一个客户会话"""

    thread_id: Optional[UUID] = Field(None, description="线程标识符")
    tenant_id: str = Field(description="租户标识符")
    assistant_id: Optional[UUID] = Field(None, description="助手标识符")
    status: ThreadStatus = Field(default=ThreadStatus.IDLE, description="线程状态")
    name: Optional[str] = Field(None, description="客户姓名")
    sex: Optional[Sex] = Field(None, description="客户性别")
    age: Optional[int] = Field(None, description="客户年龄")
    phone: Optional[str] = Field(None, description="客户电话")
    occupation: Optional[str] = Field(None, description="客户职业")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")

    @classmethod
    def to_model(cls, thread_orm: ThreadOrm) -> Self:
        """从ThreadOrm对象创建Thread Pydantic模型"""
        return cls(
            thread_id=thread_orm.thread_id,
            tenant_id=thread_orm.tenant_id,
            assistant_id=thread_orm.assistant_id,
            status=thread_orm.status,
            name=thread_orm.name,
            sex=thread_orm.sex,
            age=thread_orm.age,
            phone=thread_orm.phone,
            occupation=thread_orm.occupation,
            created_at=thread_orm.created_at,
            updated_at=thread_orm.updated_at
        )

    def to_orm(self) -> ThreadOrm:
        """转换为ThreadOrm数据库模型对象"""
        return ThreadOrm(
            thread_id=self.thread_id,
            tenant_id=self.tenant_id,
            assistant_id=self.assistant_id,
            status=self.status,
            name=self.name,
            sex=self.sex,
            age=self.age,
            phone=self.phone,
            occupation=self.occupation,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

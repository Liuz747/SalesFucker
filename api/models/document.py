"""
文档相关业务模型

该模块包含文档管理业务领域的所有模型，包括Pydantic业务模型和SQLAlchemy ORM模型。
用于RAG系统的文档上传、存储和检索功能。
"""

from datetime import datetime
from typing import Optional, Self
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB

from libs.types import DocumentStatus, DocumentType
from utils import get_current_datetime
from .base import Base


class DocumentOrm(Base):
    """文档数据库ORM模型 - 存储上传的文档元数据"""

    __tablename__ = "documents"

    document_id = Column(Uuid, primary_key=True, server_default=func.gen_random_uuid())
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户标识符")
    assistant_id = Column(String(64), nullable=True, index=True, comment="助手标识符")
    title = Column(String(255), nullable=False, comment="文档标题")
    file_url = Column(String(500), nullable=False, comment="文件存储URL（外部存储）")
    original_filename = Column(String(255), nullable=True, comment="原始文件名")
    file_type = Column(SQLEnum(DocumentType, name='document_type'), nullable=False, comment="文件类型")
    suffix = Column(String(20), nullable=True, comment="文件后缀名（如.pdf, .jpg）")
    file_size = Column(Integer, nullable=False, comment="文件大小（字节）")
    file_hash = Column(String(64), nullable=True, index=True, comment="文件SHA256哈希值")
    status = Column(SQLEnum(DocumentStatus, name='document_status'), default=DocumentStatus.PENDING, nullable=False, index=True, comment="文档状态")
    batch = Column(String(64), nullable=True, index=True, comment="批次标识符")
    position = Column(Integer, nullable=True, comment="批次内位置")
    description = Column(Text, nullable=True, comment="文档描述")
    remark = Column(Text, nullable=True, comment="备注信息")
    error = Column(Text, nullable=True, comment="错误信息（如果处理失败）")
    chunk_count = Column(Integer, default=0, nullable=False, comment="文档分块数量")
    word_count = Column(Integer, default=0, nullable=False, comment="文档字数")
    token_count = Column(Integer, default=0, nullable=False, comment="文档token总数")

    # 处理pipeline时间戳
    processing_started_at = Column(DateTime(timezone=True), nullable=True, comment="处理开始时间")
    parsing_completed_at = Column(DateTime(timezone=True), nullable=True, comment="解析完成时间")
    cleaning_completed_at = Column(DateTime(timezone=True), nullable=True, comment="清洗完成时间")
    splitting_completed_at = Column(DateTime(timezone=True), nullable=True, comment="分块完成时间")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DocumentChunkOrm(Base):
    """文档分块数据库ORM模型 - 存储文档的分块内容"""

    __tablename__ = "document_chunks"

    chunk_id = Column(Uuid, primary_key=True, server_default=func.gen_random_uuid())
    document_id = Column(Uuid, ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False, index=True, comment="所属文档ID")
    tenant_id = Column(String(64), nullable=False, index=True, comment="租户标识符")
    chunk_index = Column(Integer, nullable=False, comment="分块索引（在文档中的顺序）")
    content = Column(Text, nullable=False, comment="分块内容")
    token_count = Column(Integer, nullable=False, comment="分块token数量")
    word_count = Column(Integer, default=0, nullable=False, comment="分块字数")
    keywords = Column(JSONB, default=[], comment="关键词列表")
    answer = Column(Text, nullable=True, comment="问答对中的答案")
    hit_count = Column(Integer, default=0, nullable=False, comment="命中次数")
    status = Column(String(50), default="ACTIVE", nullable=False, comment="分块状态")
    index_node_id = Column(String(255), nullable=True, comment="向量数据库中的节点ID")
    index_node_hash = Column(String(64), nullable=True, comment="索引节点哈希值")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Document(BaseModel):
    """文档数据模型 - 用于业务逻辑层"""

    document_id: Optional[UUID] = Field(None, description="文档标识符")
    tenant_id: str = Field(description="租户标识符")
    assistant_id: Optional[str] = Field(None, description="助手标识符")
    title: str = Field(description="文档标题")
    file_url: str = Field(description="文件存储URL（外部存储）")
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_type: DocumentType = Field(description="文件类型")
    suffix: Optional[str] = Field(None, description="文件后缀名（如.pdf, .jpg）")
    file_size: int = Field(description="文件大小（字节）")
    file_hash: Optional[str] = Field(None, description="文件SHA256哈希值")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="文档状态")
    batch: Optional[str] = Field(None, description="批次标识符")
    position: Optional[int] = Field(None, description="批次内位置")
    description: Optional[str] = Field(None, description="文档描述")
    remark: Optional[str] = Field(None, description="备注信息")
    error: Optional[str] = Field(None, description="错误信息（如果处理失败）")
    chunk_count: int = Field(default=0, description="文档分块数量")
    word_count: int = Field(default=0, description="文档字数")
    token_count: int = Field(default=0, description="文档token总数")

    # 处理pipeline时间戳
    processing_started_at: Optional[datetime] = Field(None, description="处理开始时间")
    parsing_completed_at: Optional[datetime] = Field(None, description="解析完成时间")
    cleaning_completed_at: Optional[datetime] = Field(None, description="清洗完成时间")
    splitting_completed_at: Optional[datetime] = Field(None, description="分块完成时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")

    @classmethod
    def to_model(cls, document_orm: DocumentOrm) -> Self:
        """从DocumentOrm对象创建Document Pydantic模型"""
        return cls(
            document_id=document_orm.document_id,
            tenant_id=document_orm.tenant_id,
            assistant_id=document_orm.assistant_id,
            title=document_orm.title,
            file_url=document_orm.file_url,
            original_filename=document_orm.original_filename,
            file_type=document_orm.file_type,
            suffix=document_orm.suffix,
            file_size=document_orm.file_size,
            file_hash=document_orm.file_hash,
            status=document_orm.status,
            batch=document_orm.batch,
            position=document_orm.position,
            description=document_orm.description,
            remark=document_orm.remark,
            error=document_orm.error,
            chunk_count=document_orm.chunk_count,
            word_count=document_orm.word_count,
            token_count=document_orm.token_count,
            processing_started_at=document_orm.processing_started_at,
            parsing_completed_at=document_orm.parsing_completed_at,
            cleaning_completed_at=document_orm.cleaning_completed_at,
            splitting_completed_at=document_orm.splitting_completed_at,
            completed_at=document_orm.completed_at,
            created_at=document_orm.created_at,
            updated_at=document_orm.updated_at
        )

    def to_orm(self) -> DocumentOrm:
        """转换为DocumentOrm数据库模型对象"""
        return DocumentOrm(
            document_id=self.document_id,
            tenant_id=self.tenant_id,
            assistant_id=self.assistant_id,
            title=self.title,
            file_url=self.file_url,
            original_filename=self.original_filename,
            file_type=self.file_type,
            suffix=self.suffix,
            file_size=self.file_size,
            file_hash=self.file_hash,
            status=self.status,
            batch=self.batch,
            position=self.position,
            description=self.description,
            remark=self.remark,
            error=self.error,
            chunk_count=self.chunk_count,
            word_count=self.word_count,
            token_count=self.token_count,
            processing_started_at=self.processing_started_at,
            parsing_completed_at=self.parsing_completed_at,
            cleaning_completed_at=self.cleaning_completed_at,
            splitting_completed_at=self.splitting_completed_at,
            completed_at=self.completed_at,
            created_at=self.created_at,
            updated_at=self.updated_at
        )


class DocumentChunk(BaseModel):
    """文档分块数据模型 - 用于业务逻辑层"""

    chunk_id: Optional[UUID] = Field(None, description="分块标识符")
    document_id: UUID = Field(description="所属文档ID")
    tenant_id: str = Field(description="租户标识符")
    chunk_index: int = Field(description="分块索引（在文档中的顺序）")
    content: str = Field(description="分块内容")
    token_count: int = Field(description="分块token数量")
    word_count: int = Field(default=0, description="分块字数")
    keywords: list[str] = Field(default_factory=list, description="关键词列表")
    answer: Optional[str] = Field(None, description="问答对中的答案")
    hit_count: int = Field(default=0, description="命中次数")
    status: str = Field(default="ACTIVE", description="分块状态")
    index_node_id: Optional[str] = Field(None, description="向量数据库中的节点ID")
    index_node_hash: Optional[str] = Field(None, description="索引节点哈希值")
    created_at: datetime = Field(default_factory=get_current_datetime, description="创建时间")
    updated_at: datetime = Field(default_factory=get_current_datetime, description="更新时间")

    @classmethod
    def to_model(cls, chunk_orm: DocumentChunkOrm) -> Self:
        """从DocumentChunkOrm对象创建DocumentChunk Pydantic模型"""
        return cls(
            chunk_id=chunk_orm.chunk_id,
            document_id=chunk_orm.document_id,
            tenant_id=chunk_orm.tenant_id,
            chunk_index=chunk_orm.chunk_index,
            content=chunk_orm.content,
            token_count=chunk_orm.token_count,
            word_count=chunk_orm.word_count,
            keywords=chunk_orm.keywords or [],
            answer=chunk_orm.answer,
            hit_count=chunk_orm.hit_count,
            status=chunk_orm.status,
            index_node_id=chunk_orm.index_node_id,
            index_node_hash=chunk_orm.index_node_hash,
            created_at=chunk_orm.created_at,
            updated_at=chunk_orm.updated_at
        )

    def to_orm(self) -> DocumentChunkOrm:
        """转换为DocumentChunkOrm数据库模型对象"""
        return DocumentChunkOrm(
            chunk_id=self.chunk_id,
            document_id=self.document_id,
            tenant_id=self.tenant_id,
            chunk_index=self.chunk_index,
            content=self.content,
            token_count=self.token_count,
            word_count=self.word_count,
            keywords=self.keywords,
            answer=self.answer,
            hit_count=self.hit_count,
            status=self.status,
            index_node_id=self.index_node_id,
            index_node_hash=self.index_node_hash,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

"""
文档管理相关的请求和响应模式
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from libs.types import DocumentStatus, DocumentType
from .responses import BaseResponse


class DocumentUploadRequest(BaseModel):
    """文档上传请求模型"""

    title: Optional[str] = Field(None, description="文档标题（可选，默认使用文件名）")


class DocumentMetadataRequest(BaseModel):
    """文档元数据创建请求（用于外部存储场景）"""

    file_url: str = Field(description="文件存储URL（外部系统提供）")
    original_filename: str = Field(description="原始文件名")
    file_size: int = Field(gt=0, description="文件大小（字节）")
    file_hash: Optional[str] = Field(None, description="文件SHA256哈希值")
    mime_type: Optional[str] = Field(None, description="MIME类型")

    title: Optional[str] = Field(None, description="文档标题（可选，默认使用文件名）")


class DocumentUploadResponse(BaseResponse):
    """文档上传响应模型"""

    document_id: UUID = Field(description="上传的文档ID")
    title: str = Field(description="文档标题")
    file_type: DocumentType = Field(description="文件类型")
    file_size: int = Field(description="文件大小（字节）")
    status: DocumentStatus = Field(description="文档状态")


class DocumentUpdateRequest(BaseModel):
    """文档元数据更新请求模型"""

    title: Optional[str] = Field(None, description="文档标题")


class DocumentResponse(BaseResponse):
    """文档详情响应模型"""

    document_id: UUID = Field(description="文档ID")
    tenant_id: str = Field(description="租户ID")
    assistant_id: Optional[str] = Field(None, description="助手ID")
    title: str = Field(description="文档标题")
    file_path: str = Field(description="文件存储路径或URL")
    original_filename: Optional[str] = Field(None, description="原始文件名")
    file_type: DocumentType = Field(description="文件类型")
    suffix: Optional[str] = Field(None, description="文件后缀名（如.pdf, .jpg）")
    file_size: int = Field(description="文件大小（字节）")
    file_hash: Optional[str] = Field(None, description="文件SHA256哈希值")
    mime_type: Optional[str] = Field(None, description="MIME类型")
    status: DocumentStatus = Field(description="文档状态")
    batch: Optional[str] = Field(None, description="批次标识符")
    position: Optional[int] = Field(None, description="批次内位置")
    description: Optional[str] = Field(None, description="文档描述")
    remark: Optional[str] = Field(None, description="备注信息")
    error: Optional[str] = Field(None, description="错误信息（如果处理失败）")
    chunk_count: int = Field(description="文档分块数量")
    word_count: int = Field(default=0, description="文档字数")
    token_count: int = Field(default=0, description="文档token总数")

    # 处理pipeline时间戳
    processing_started_at: Optional[datetime] = Field(None, description="处理开始时间")
    parsing_completed_at: Optional[datetime] = Field(None, description="解析完成时间")
    cleaning_completed_at: Optional[datetime] = Field(None, description="清洗完成时间")
    splitting_completed_at: Optional[datetime] = Field(None, description="分块完成时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class DocumentProcessingStatusResponse(BaseResponse):
    """文档处理状态响应（详细的pipeline状态）"""

    document_id: UUID = Field(description="文档ID")
    status: DocumentStatus = Field(description="文档状态")
    current_stage: str = Field(description="当前处理阶段")

    # Pipeline时间戳
    processing_started_at: Optional[datetime] = Field(None, description="处理开始时间")
    parsing_completed_at: Optional[datetime] = Field(None, description="解析完成时间")
    cleaning_completed_at: Optional[datetime] = Field(None, description="清洗完成时间")
    splitting_completed_at: Optional[datetime] = Field(None, description="分块完成时间")
    indexing_completed_at: Optional[datetime] = Field(None, description="索引完成时间")

    # 内容指标
    word_count: int = Field(default=0, description="文档字数")
    token_count: int = Field(default=0, description="文档token总数")
    chunk_count: int = Field(default=0, description="文档分块数量")

    # 错误追踪
    error: Optional[str] = Field(None, description="错误信息（如果处理失败）")


class DocumentListResponse(BaseResponse):
    """文档列表响应模型"""

    documents: list[DocumentResponse] = Field(description="文档列表")
    total: int = Field(description="文档总数")
    limit: int = Field(description="返回数量限制")
    offset: int = Field(description="偏移量")


class DocumentDeleteResponse(BaseResponse):
    """文档删除响应模型"""

    document_id: UUID = Field(description="删除的文档ID")
    success: bool = Field(description="是否删除成功")


class DocumentIndexRequest(BaseModel):
    """文档索引请求模型"""

    document_id: UUID = Field(description="要索引的文档ID")


class DocumentIndexResponse(BaseResponse):
    """文档索引响应模型"""

    document_id: UUID = Field(description="文档ID")
    status: DocumentStatus = Field(description="索引后的文档状态")
    chunk_count: int = Field(description="生成的分块数量")


class DocumentBatchIndexRequest(BaseModel):
    """批量文档索引请求模型"""

    document_ids: list[UUID] = Field(description="要索引的文档ID列表", min_length=1, max_length=100)


class DocumentBatchIndexResponse(BaseResponse):
    """批量文档索引响应模型"""

    succeeded: int = Field(description="成功索引的文档数量")
    failed: int = Field(description="失败的文档数量")
    failed_ids: list[UUID] = Field(description="失败的文档ID列表")

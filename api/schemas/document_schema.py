"""
文档管理相关的请求和响应模式
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from libs.types import DocumentStatus
from models import Document
from .responses import BaseResponse


class DocumentUploadRequest(BaseModel):
    """文档数据创建请求"""

    assistant_id: Optional[str] = Field(None, description="助手标识符")
    title: Optional[str] = Field(None, description="文档标题（可选，默认使用原始文件名）")
    original_filename: str = Field(description="原始文件名")
    file_url: str = Field(description="文件存储URL（外部存储系统）")
    batch: Optional[str] = Field(None, description="批次标识符")
    description: Optional[str] = Field(None, description="文档描述")
    remark: Optional[str] = Field(None, description="备注信息")


class DocumentUploadResponse(BaseResponse):
    """文档上传响应模型"""

    document_id: UUID = Field(description="上传的文档ID")


class DocumentUpdateRequest(BaseModel):
    """文档元数据更新请求模型"""

    title: Optional[str] = Field(None, description="文档标题")
    description: Optional[str] = Field(None, description="文档描述")
    remark: Optional[str] = Field(None, description="备注信息")


class DocumentListRequest(BaseModel):
    """文档列表查询请求模型"""

    limit: int = Field(100, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")
    status: Optional[DocumentStatus] = Field(None, description="文档状态过滤")


class DocumentResponse(BaseResponse):
    """文档详情响应模型"""

    data: Document = Field(description="文档数据")


# Following not been verified
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
    completed_at: Optional[datetime] = Field(None, description="完成时间")

    # 内容指标
    word_count: int = Field(default=0, description="文档字数")
    token_count: int = Field(default=0, description="文档token总数")
    chunk_count: int = Field(default=0, description="文档分块数量")

    # 错误追踪
    error: Optional[str] = Field(None, description="错误信息（如果处理失败）")


class DocumentListResponse(BaseResponse):
    """文档列表响应模型"""

    data: list[Document] = Field(description="文档列表")
    total: int = Field(description="文档总数")
    limit: int = Field(description="返回数量限制")
    offset: int = Field(description="偏移量")


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

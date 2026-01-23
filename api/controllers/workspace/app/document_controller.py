"""
文档管理API端点

该模块提供文档管理的REST API端点，包括上传、查询、更新、删除等功能。
支持完整的文档生命周期管理，为RAG系统提供知识库管理能力。

主要端点:
- POST /v1/documents/upload - 上传文档
- GET /v1/documents - 获取文档列表
- GET /v1/documents/{document_id} - 获取文档详情
- PATCH /v1/documents/{document_id} - 更新文档元数据
- DELETE /v1/documents/{document_id} - 删除文档
- GET /v1/documents/{document_id}/content - 获取文档内容
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from libs.exceptions import (
    BaseHTTPException,
    DocumentException,
    DocumentNotFoundException,
    DocumentUploadException,
    DocumentDeletionException,
    DocumentProcessingException
)
from models import Document, DocumentStatus, TenantModel
from schemas import (
    DocumentUploadResponse,
    DocumentMetadataRequest,
    DocumentUpdateRequest,
    DocumentResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentBatchIndexRequest,
    DocumentBatchIndexResponse,
    DocumentProcessingStatusResponse,
    BaseResponse
)
from services import DocumentService
from utils import get_component_logger
from ..wraps import validate_and_get_tenant

logger = get_component_logger(__name__)


# 创建路由器
router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    file: UploadFile = File(..., description="要上传的文档文件"),
    title: Optional[str] = Form(None, description="文档标题（可选，默认使用文件名）")
):
    """
    上传文档

    上传一个新文档到系统，支持TXT、MD、PDF、DOCX格式。
    文件大小限制为10MB。

    参数:
        file: 文档文件
        title: 文档标题（可选）

    返回:
        DocumentUploadResponse: 上传结果
    """
    try:
        logger.info(f"上传文档请求: tenant={tenant.tenant_id}, filename={file.filename}")

        # 读取文件内容
        file_content = await file.read()

        # 调用服务层上传文档
        document_id = await DocumentService.upload_document(
            tenant_id=tenant.tenant_id,
            filename=file.filename,
            file_content=file_content,
            title=title
        )

        # 获取文档信息
        document = await DocumentService.get_document(document_id)

        logger.info(f"文档上传成功: {document_id}")

        return DocumentUploadResponse(
            message="文档上传成功",
            document_id=document.document_id,
            title=document.title,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status
        )

    except BaseHTTPException:
        raise
    except ValueError as e:
        logger.error(f"文档上传失败（参数错误）: {e}")
        raise DocumentUploadException(str(e))
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise DocumentUploadException(str(e))


@router.post("/metadata", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_document_metadata(
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    request: DocumentMetadataRequest
):
    """
    创建文档元数据（用于外部存储场景）

    适用于文件已存储在外部系统（如OSS、S3）的场景。
    只存储元数据和URL引用，不上传实际文件。
    支持基于文件哈希的自动去重。

    参数:
        request: 文档元数据请求

    返回:
        DocumentUploadResponse: 创建结果
    """
    try:
        logger.info(f"创建文档元数据请求: tenant={tenant.tenant_id}, filename={request.original_filename}")

        # 调用服务层创建文档元数据
        document_id = await DocumentService.create_document_metadata(
            tenant_id=tenant.tenant_id,
            file_url=request.file_url,
            original_filename=request.original_filename,
            file_size=request.file_size,
            file_hash=request.file_hash,
            mime_type=request.mime_type,
            title=request.title
        )

        # 获取文档信息
        document = await DocumentService.get_document(document_id)

        logger.info(f"文档元数据创建成功: {document_id}")

        return DocumentUploadResponse(
            message="文档元数据创建成功",
            document_id=document.document_id,
            title=document.title,
            file_type=document.file_type,
            file_size=document.file_size,
            status=document.status
        )

    except BaseHTTPException:
        raise
    except ValueError as e:
        logger.error(f"创建文档元数据失败（参数错误）: {e}")
        raise DocumentUploadException(str(e))
    except Exception as e:
        logger.error(f"创建文档元数据失败: {e}")
        raise DocumentUploadException(str(e))


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    status: Optional[DocumentStatus] = Query(None, description="文档状态过滤")
):
    """
    获取文档列表

    获取租户的文档列表，支持分页和状态过滤。

    参数:
        limit: 返回数量限制（1-1000）
        offset: 偏移量
        status: 文档状态过滤（可选）

    返回:
        DocumentListResponse: 文档列表
    """
    try:
        logger.info(f"查询文档列表: tenant={tenant.tenant_id}, limit={limit}, offset={offset}")

        documents = await DocumentService.get_documents_by_tenant(
            tenant_id=tenant.tenant_id,
            limit=limit,
            offset=offset,
            status=status
        )

        # 转换为响应模型
        document_responses = [
            DocumentResponse(
                message="成功",
                document_id=doc.document_id,
                tenant_id=doc.tenant_id,
                assistant_id=doc.assistant_id,
                title=doc.title,
                file_path=doc.file_path,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                suffix=doc.suffix,
                file_size=doc.file_size,
                file_hash=doc.file_hash,
                mime_type=doc.mime_type,
                status=doc.status,
                batch=doc.batch,
                position=doc.position,
                description=doc.description,
                remark=doc.remark,
                error=doc.error,
                chunk_count=doc.chunk_count,
                word_count=doc.word_count,
                token_count=doc.token_count,
                processing_started_at=doc.processing_started_at,
                parsing_completed_at=doc.parsing_completed_at,
                cleaning_completed_at=doc.cleaning_completed_at,
                splitting_completed_at=doc.splitting_completed_at,
                completed_at=doc.completed_at,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            for doc in documents
        ]

        logger.info(f"文档列表查询成功: 返回 {len(document_responses)} 个文档")

        return DocumentListResponse(
            message="成功",
            documents=document_responses,
            total=len(document_responses),
            limit=limit,
            offset=offset
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"文档列表查询失败: {e}")
        raise DocumentException()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取文档详情

    根据文档ID获取完整的文档信息。

    参数:
        document_id: 文档ID

    返回:
        DocumentResponse: 文档详情
    """
    try:
        logger.info(f"查询文档详情: document={document_id}")

        document = await DocumentService.get_document(document_id)

        if not document:
            raise DocumentNotFoundException(document_id)

        # 验证租户权限
        if document.tenant_id != tenant.tenant_id:
            raise DocumentNotFoundException(document_id)

        logger.info(f"文档详情查询成功: {document_id}")

        return DocumentResponse(
            message="成功",
            document_id=document.document_id,
            tenant_id=document.tenant_id,
            assistant_id=document.assistant_id,
            title=document.title,
            file_path=document.file_path,
            original_filename=document.original_filename,
            file_type=document.file_type,
            suffix=document.suffix,
            file_size=document.file_size,
            file_hash=document.file_hash,
            mime_type=document.mime_type,
            status=document.status,
            batch=document.batch,
            position=document.position,
            description=document.description,
            remark=document.remark,
            error=document.error,
            chunk_count=document.chunk_count,
            word_count=document.word_count,
            token_count=document.token_count,
            processing_started_at=document.processing_started_at,
            parsing_completed_at=document.parsing_completed_at,
            cleaning_completed_at=document.cleaning_completed_at,
            splitting_completed_at=document.splitting_completed_at,
            completed_at=document.completed_at,
            created_at=document.created_at,
            updated_at=document.updated_at
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"文档详情查询失败: {e}")
        raise DocumentException()


@router.patch("/{document_id}", response_model=BaseResponse)
async def update_document(
    document_id: UUID,
    request: DocumentUpdateRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    更新文档元数据

    更新指定文档的元数据信息，支持部分字段更新。

    参数:
        document_id: 文档ID
        request: 更新请求

    返回:
        BaseResponse: 更新结果
    """
    try:
        logger.info(f"更新文档请求: document={document_id}")

        # 验证文档存在且属于当前租户
        document = await DocumentService.get_document(document_id)
        if not document:
            raise DocumentNotFoundException(document_id)
        if document.tenant_id != tenant.tenant_id:
            raise DocumentNotFoundException(document_id)

        # 更新文档元数据
        await DocumentService.update_document_metadata(
            document_id=document_id,
            title=request.title
        )

        logger.info(f"文档更新成功: {document_id}")
        return BaseResponse(message="文档更新成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"文档更新失败: {e}")
        raise DocumentException()


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    删除文档

    删除指定的文档及其相关数据（包括文件和分块）。

    参数:
        document_id: 文档ID

    返回:
        DocumentDeleteResponse: 删除结果
    """
    try:
        logger.info(f"删除文档请求: document={document_id}")

        # 验证文档存在且属于当前租户
        document = await DocumentService.get_document(document_id)
        if not document:
            raise DocumentNotFoundException(document_id)
        if document.tenant_id != tenant.tenant_id:
            raise DocumentNotFoundException(document_id)

        # 删除文档
        success = await DocumentService.delete_document(document_id)

        logger.info(f"文档删除成功: {document_id}")

        return DocumentDeleteResponse(
            message="文档删除成功",
            document_id=document_id,
            success=success
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"文档删除失败: {e}")
        raise DocumentDeletionException(document_id, str(e))


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取文档内容

    获取文档的原始文件内容。

    参数:
        document_id: 文档ID

    返回:
        文件内容（二进制）
    """
    try:
        from fastapi.responses import Response

        logger.info(f"获取文档内容: document={document_id}")

        # 验证文档存在且属于当前租户
        document = await DocumentService.get_document(document_id)
        if not document:
            raise DocumentNotFoundException(document_id)
        if document.tenant_id != tenant.tenant_id:
            raise DocumentNotFoundException(document_id)

        # 获取文档内容
        content = await DocumentService.get_document_content(document_id)
        if not content:
            raise DocumentNotFoundException(document_id)

        logger.info(f"文档内容获取成功: {document_id}")

        # 返回文件内容
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={document.title}"
            }
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档内容失败: {e}")
        raise DocumentException()


@router.post("/{document_id}/index", response_model=BaseResponse)
async def index_document(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    索引文档

    处理文档并将其索引到向量数据库和搜索引擎。

    参数:
        document_id: 文档ID

    返回:
        BaseResponse: 索引结果
    """
    try:
        from core.rag.indexing import document_indexer

        logger.info(f"索引文档请求: document={document_id}")

        # 验证文档存在且属于当前租户
        document = await DocumentService.get_document(document_id)
        if not document:
            raise DocumentNotFoundException(document_id)
        if document.tenant_id != tenant.tenant_id:
            raise DocumentNotFoundException(document_id)

        # 执行索引
        result = await document_indexer.index_document(document_id)

        if result.success:
            logger.info(f"文档索引成功: {document_id}, 分块数: {result.chunk_count}")
            return BaseResponse(
                message=f"文档索引成功，生成 {result.chunk_count} 个分块"
            )
        else:
            logger.error(f"文档索引失败: {document_id}, 错误: {result.error}")
            raise DocumentProcessingException(document_id, result.error)

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"文档索引失败: {e}")
        raise DocumentProcessingException(document_id, str(e))


@router.post("/batch-index", response_model=BaseResponse)
async def batch_index_documents(
    request: DocumentBatchIndexRequest,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    批量索引文档

    批量处理多个文档并索引。

    参数:
        request: 批量索引请求

    返回:
        DocumentBatchIndexResponse: 批量索引结果
    """
    try:
        from core.rag.indexing import document_indexer

        logger.info(f"批量索引文档请求: {len(request.document_ids)} 个文档")

        # 验证所有文档属于当前租户
        for document_id in request.document_ids:
            document = await DocumentService.get_document(document_id)
            if not document:
                raise DocumentNotFoundException(document_id)
            if document.tenant_id != tenant.tenant_id:
                raise DocumentNotFoundException(document_id)

        # 执行批量索引
        results = await document_indexer.index_documents_batch(request.document_ids)

        # 统计结果
        succeeded = sum(1 for r in results.values() if r.success)
        failed = len(results) - succeeded
        failed_ids = [
            UUID(doc_id) for doc_id, r in results.items() if not r.success
        ]

        logger.info(f"批量索引完成: 成功 {succeeded}, 失败 {failed}")

        return DocumentBatchIndexResponse(
            message=f"批量索引完成: 成功 {succeeded}, 失败 {failed}",
            succeeded=succeeded,
            failed=failed,
            failed_ids=failed_ids
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"批量索引失败: {e}")
        raise DocumentException()


@router.get("/{document_id}/index-status", response_model=DocumentResponse)
async def get_index_status(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取文档索引状态

    查询文档的索引状态和分块信息。

    参数:
        document_id: 文档ID

    返回:
        DocumentResponse: 文档状态信息
    """
    try:
        logger.info(f"查询文档索引状态: document={document_id}")

        document = await DocumentService.get_document(document_id)
        if not document:
            raise DocumentNotFoundException(document_id)
        if document.tenant_id != tenant.tenant_id:
            raise DocumentNotFoundException(document_id)

        logger.info(f"文档索引状态: {document.status}, 分块数: {document.chunk_count}")

        return DocumentResponse(
            message="成功",
            document_id=document.document_id,
            tenant_id=document.tenant_id,
            assistant_id=document.assistant_id,
            title=document.title,
            file_path=document.file_path,
            original_filename=document.original_filename,
            file_type=document.file_type,
            suffix=document.suffix,
            file_size=document.file_size,
            file_hash=document.file_hash,
            mime_type=document.mime_type,
            status=document.status,
            batch=document.batch,
            position=document.position,
            description=document.description,
            remark=document.remark,
            error=document.error,
            chunk_count=document.chunk_count,
            word_count=document.word_count,
            token_count=document.token_count,
            processing_started_at=document.processing_started_at,
            parsing_completed_at=document.parsing_completed_at,
            cleaning_completed_at=document.cleaning_completed_at,
            splitting_completed_at=document.splitting_completed_at,
            completed_at=document.completed_at,
            created_at=document.created_at,
            updated_at=document.updated_at
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"查询文档索引状态失败: {e}")
        raise DocumentException()


@router.get("/{document_id}/processing-status", response_model=DocumentProcessingStatusResponse)
async def get_processing_status(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取文档处理的详细状态

    返回处理pipeline各阶段的时间戳和进度信息。
    包括解析、清洗、分块、索引等各个阶段的完成时间。

    参数:
        document_id: 文档ID

    返回:
        DocumentProcessingStatusResponse: 详细的处理状态信息
    """
    try:
        logger.info(f"查询文档处理状态: document={document_id}")

        document = await DocumentService.get_document(document_id)
        if not document:
            raise DocumentNotFoundException(document_id)
        if document.tenant_id != tenant.tenant_id:
            raise DocumentNotFoundException(document_id)

        # 确定当前处理阶段
        current_stage = "pending"
        if document.processing_started_at:
            current_stage = "parsing"
        if document.parsing_completed_at:
            current_stage = "cleaning"
        if document.cleaning_completed_at:
            current_stage = "splitting"
        if document.splitting_completed_at:
            current_stage = "indexing"
        if document.indexing_completed_at:
            current_stage = "completed"
        if document.status == DocumentStatus.FAILED:
            current_stage = "failed"

        logger.info(f"文档处理状态: {document.status}, 当前阶段: {current_stage}")

        return DocumentProcessingStatusResponse(
            message="成功",
            document_id=document.document_id,
            status=document.status,
            current_stage=current_stage,
            processing_started_at=document.processing_started_at,
            parsing_completed_at=document.parsing_completed_at,
            cleaning_completed_at=document.cleaning_completed_at,
            splitting_completed_at=document.splitting_completed_at,
            indexing_completed_at=document.indexing_completed_at,
            word_count=document.word_count,
            token_count=document.token_count,
            chunk_count=document.chunk_count,
            error=document.error
        )

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"查询文档处理状态失败: {e}")
        raise DocumentException()

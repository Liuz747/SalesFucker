from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from core.rag.indexing import document_indexer
from libs.exceptions import (
    BaseHTTPException,
    DocumentException,
    DocumentNotFoundException,
    DocumentProcessingException
)
from libs.types import DocumentStatus
from models import TenantModel
from schemas import (
    BaseResponse,
    DocumentBatchIndexRequest,
    DocumentBatchIndexResponse,
    DocumentProcessingStatusResponse
)
from services import DocumentService
from utils import get_component_logger
from ..wraps import validate_and_get_tenant

logger = get_component_logger(__name__)

router = APIRouter()


@router.post("/{document_id}/index", response_model=BaseResponse)
async def index_document(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    索引文档

    处理文档并将其索引到向量数据库和搜索引擎。
    """
    try:
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
    """
    try:
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

        # 安全地转换字典键为UUID，处理可能的转换错误
        failed_ids = []
        for doc_id, r in results.items():
            if not r.success:
                try:
                    failed_ids.append(UUID(doc_id) if isinstance(doc_id, str) else doc_id)
                except (ValueError, AttributeError) as e:
                    logger.error(f"无法将文档ID转换为UUID: {doc_id}, 错误: {e}")
                    # 如果转换失败，记录错误但继续处理其他ID

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


@router.get("/{document_id}/processing-status", response_model=DocumentProcessingStatusResponse)
async def get_processing_status(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    获取文档处理的详细状态

    返回处理pipeline各阶段的时间戳和进度信息。
    包括解析、清洗、分块、索引等各个阶段的完成时间。
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
        if document.completed_at:
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
            completed_at=document.completed_at,
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

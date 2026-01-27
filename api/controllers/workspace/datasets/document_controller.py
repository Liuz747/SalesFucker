"""
文档管理API端点

该模块提供文档管理的REST API端点，包括上传、查询、更新、删除等功能。
支持完整的文档生命周期管理，为RAG系统提供知识库管理能力。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from libs.exceptions import (
    BaseHTTPException,
    DocumentException,
    DocumentNotFoundException,
    DocumentUploadException,
    DocumentDeletionException
)
from models import TenantModel
from schemas import (
    BaseResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentUpdateRequest,
    DocumentListRequest,
    DocumentResponse,
    DocumentListResponse
)
from services import DocumentService
from utils import get_component_logger
from .segments import router as segments_router
from ..wraps import validate_and_get_tenant

logger = get_component_logger(__name__)


# 创建路由器
router = APIRouter()

router.include_router(segments_router)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_document_metadata(
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    request: DocumentUploadRequest
):
    """
    创建文档数据

    只存储元数据和URL引用，不上传实际文件。
    """
    try:
        logger.info(f"创建文档元数据请求: tenant={tenant.tenant_id}, filename={request.original_filename}")

        # 调用服务层创建文档元数据
        document_id = await DocumentService.create_document_metadata(
            tenant_id=tenant.tenant_id,
            file_url=request.file_url,
            original_filename=request.original_filename,
            title=request.title,
            description=request.description,
            remark=request.remark,
            batch=request.batch
        )

        # 获取文档信息
        document = await DocumentService.get_document(document_id)

        logger.info(f"文档元数据创建成功: {document_id}")

        return DocumentUploadResponse(
            message="文档元数据创建成功",
            document_id=document.document_id
        )

    except BaseHTTPException:
        raise
    except ValueError as e:
        logger.error(f"创建文档元数据失败（参数错误）: {e}")
        raise DocumentUploadException(str(e))
    except Exception as e:
        logger.error(f"创建文档元数据失败: {e}")
        raise DocumentUploadException(str(e))


@router.get("/list-page", response_model=DocumentListResponse)
async def list_documents(
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)],
    request: DocumentListRequest
):
    """
    获取文档列表

    获取租户的文档列表，支持分页和状态过滤。
    """
    try:
        logger.info(f"查询文档列表: tenant={tenant.tenant_id}, limit={request.limit}, offset={request.offset}")

        documents, total = await DocumentService.get_documents_by_tenant(
            tenant_id=tenant.tenant_id,
            limit=request.limit,
            offset=request.offset,
            status=request.status
        )

        logger.info(f"文档列表查询成功: 返回 {len(documents)} 个文档，总数: {total}")

        return DocumentListResponse(
            message="成功",
            data=documents,
            total=total,
            limit=request.limit,
            offset=request.offset
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
            data=document
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
            title=request.title,
            description=request.description,
            remark=request.remark
        )

        logger.info(f"文档更新成功: {document_id}")
        return BaseResponse(message="文档更新成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"文档更新失败: {e}")
        raise DocumentException()


@router.delete("/{document_id}", response_model=BaseResponse)
async def delete_document(
    document_id: UUID,
    tenant: Annotated[TenantModel, Depends(validate_and_get_tenant)]
):
    """
    删除文档

    删除指定的文档及其相关数据（包括文件和分块）
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
        await DocumentService.delete_document(document_id)

        logger.info(f"文档删除成功: {document_id}")

        return BaseResponse(message="文档删除成功")

    except BaseHTTPException:
        raise
    except Exception as e:
        logger.error(f"文档删除失败: {e}")
        raise DocumentDeletionException(document_id, str(e))

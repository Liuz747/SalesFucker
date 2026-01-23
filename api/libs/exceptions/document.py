from uuid import UUID

from .base import BaseHTTPException


# ============================================
# 文档相关异常
# ============================================

class DocumentException(BaseHTTPException):
    """文档异常基类"""
    code = 1800000
    message = "DOCUMENT_ERROR"
    http_status_code = 400


class DocumentNotFoundException(DocumentException):
    """文档不存在异常"""
    code = 1800001
    message = "DOCUMENT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, document_id: UUID):
        super().__init__(detail=f"文档 {document_id} 不存在")


class DocumentUploadException(DocumentException):
    """文档上传失败异常"""
    code = 1800002
    message = "DOCUMENT_UPLOAD_FAILED"
    http_status_code = 500

    def __init__(self, reason: str = ""):
        detail = "文档上传失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class DocumentProcessingException(DocumentException):
    """文档处理失败异常"""
    code = 1800003
    message = "DOCUMENT_PROCESSING_FAILED"
    http_status_code = 500

    def __init__(self, document_id: UUID, reason: str = ""):
        detail = f"文档 {document_id} 处理失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class DocumentDeletionException(DocumentException):
    """文档删除失败异常"""
    code = 1800004
    message = "DOCUMENT_DELETION_FAILED"
    http_status_code = 500

    def __init__(self, document_id: UUID, reason: str = ""):
        detail = f"文档 {document_id} 删除失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)

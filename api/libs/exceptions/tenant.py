"""
租户相关异常

包含租户管理、验证、访问控制等相关的异常定义。
"""

from .base import BaseHTTPException


class TenantManagementException(BaseHTTPException):
    """租户管理异常基类"""
    code = 100000
    message = "TENANT_MANAGEMENT_ERROR"
    http_status_code = 500


class TenantNotFoundException(TenantManagementException):
    """租户不存在异常"""
    code = 1000002
    message = "TENANT_NOT_FOUND"
    http_status_code = 404

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 不存在")


class TenantSyncException(TenantManagementException):
    """租户同步失败异常"""
    code = 1000003
    message = "TENANT_SYNC_FAILED"
    http_status_code = 400

    def __init__(self, tenant_id: str, reason: str = ""):
        detail = f"租户 {tenant_id} 同步失败"
        if reason:
            detail += f": {reason}"
        super().__init__(detail=detail)


class TenantValidationException(BaseHTTPException):
    """租户验证异常基类"""
    code = 1000005
    message = "TENANT_VALIDATION_ERROR"
    http_status_code = 403

    def __init__(self, tenant_id: str, reason: str):
        super().__init__(detail=f"租户 {tenant_id} 验证失败: {reason}")


class TenantIdRequiredException(BaseHTTPException):
    """租户ID必填异常"""
    code = 1000006
    message = "TENANT_ID_REQUIRED"
    http_status_code = 400

    def __init__(self):
        super().__init__(detail="请求必须包含租户ID，请在请求头中添加 X-Tenant-ID")


class TenantDisabledException(TenantValidationException):
    """租户已禁用异常"""
    code = 1000008
    message = "TENANT_DISABLED"

    def __init__(self, tenant_id: str):
        super().__init__(tenant_id=tenant_id, reason="租户已被禁用")


class TenantAccessDeniedException(TenantValidationException):
    """租户访问拒绝异常"""
    code = 1000009
    message = "TENANT_ACCESS_DENIED"

    def __init__(self, tenant_id: str, resource: str):
        super().__init__(tenant_id=tenant_id, reason=f"无权访问 {resource}")


class TenantAlreadyExistsException(TenantManagementException):
    """租户已存在异常"""
    code = 1000001
    message = "TENANT_ALREADY_EXISTS"
    http_status_code = 409

    def __init__(self, tenant_id: str):
        super().__init__(detail=f"租户 {tenant_id} 已存在")